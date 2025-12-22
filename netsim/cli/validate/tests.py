#
# The main test-execution code of the "netlab validate" command
#
import argparse
import math
import sys
import time
import typing

from box import Box

from ... import data
from ...augment import devices as _devices
from ...utils import log
from . import devices, plugin, report, suzieq, utils

'''
extend_first_wait_time: some devices need extra time to start working, even when
the configuration process has completed. Assuming we can't (or don't want to)
catch that during the device readiness check, we should add extra delay to the
validation process.

This function walks through the lab nodes, checks the features.initial.delay of
each device, and adds the maximum delay to the first 'wait' parameter.
'''

def extend_first_wait_time(args: argparse.Namespace, topology: Box) -> None:
  max_delay = 0
  d_device  = None
  for n_data in topology.nodes.values():
    d_features = _devices.get_device_features(n_data,topology.defaults)
    d_delay = d_features.get('initial.delay',None)
    if not d_delay:
      continue
    if d_delay > max_delay:                                           # Found a device that requires a delay
      max_delay = d_delay                                             # ... take the max value of the delay
      d_device  = n_data.device                                       # ... and remember the device causing it

  if not max_delay:                                                   # No slow devices in lab topology, exit
    return

  for v_entry in topology.validate:
    if not v_entry.get('wait',0):                                     # No wait associated with this entry, move on
      continue

    v_entry.wait = v_entry.wait + max_delay
    if not args.error_only:
      indent = (topology._v_len + 3) if topology else 10
      log.warning(
        text=f'Initial wait time extended by {max_delay} seconds required by {d_device}',
        module='-',indent=indent)
    return

'''
Wait times for individual validation steps can be extended with the
netlab_validate.test_name.wait device settings. Used for weird devices
like junos-vrouter that passes packets between bridged ports immediately
but fails to pass them to the routed interface of the same VLAN
'''
def extend_device_wait_time(v_entry: Box, topology: Box) -> None:
  for ndata in topology.nodes.values():
    d_path = f'defaults.devices.{ndata.device}.netlab_validate.{v_entry.name}'
    v_params = topology.get(d_path,{})
    if not v_params:
      continue
    if not isinstance(v_params,Box):
      log.warning(
        text=f'{d_path} is not a dictionary, ignoring')
      continue
    v_wait = v_entry.get('wait',0)                # Get the test wait time
    if not isinstance(v_wait,int):                # Always override symbolic wait times with device-specific times
      v_wait = 0
    if 'wait' in v_params and v_params.wait > v_wait:
      if log.VERBOSE:
        print(f'Extending wait time for test {v_entry.name} to {v_params.wait} (device {ndata.device})')
      v_entry.wait = v_params.wait
    if 'level' in v_params:
      if log.VERBOSE:
        print(f'Changing severity level for test {v_entry.name} to {v_params.level} (device {ndata.device})')
      v_entry.level = v_params.level

'''
wait_before_testing -- wait for specified time since lab start time or previous test
'''
def wait_before_testing(
      v_entry: Box,
      start_time: typing.Optional[typing.Union[int,float]],
      topology: Box) -> None:
  if not 'wait' in v_entry:
    return

  if start_time is None:
    wait_time = v_entry.wait
  else:
    wait_time = math.ceil(start_time + v_entry.wait - time.time())

  if wait_time > 0 and 'wait_msg' in v_entry:         # Print the initial "we're waiting for this" message
    report.log_info(
      v_entry.wait_msg,
      f_status = 'WAITING',
      topology=topology)

  while wait_time >= 0:
    report.log_info(                                  # Have to wait some more, print a logging message
      f'Waiting for {v_entry.wait} seconds, {wait_time} seconds left',
      f_status = 'WAITING',
      topology=topology)

    time.sleep(wait_time if wait_time < 5 else 5)     # Wait no more than five seconds
    wait_time = wait_time - 5

'''
Execute node validation
'''
def execute_node_validation(
      v_entry: Box,
      topology: Box,
      n_name: str,
      report_error: bool,
      args: argparse.Namespace) -> typing.Tuple[typing.Optional[bool],typing.Optional[bool]]:

  from . import TEST_COUNT

  node = topology.nodes[n_name]
  result = data.get_empty_box()

  action = utils.find_test_action(v_entry,node) # Find the action to show/execute/wait
  if action == 'wait':                          # Test with pure 'wait'
    return (True,True)                          # is assumed to be successful

  if action is None:                            # None found, skip this node
    report.log_info(
      f'Test action not defined for device {node.device} / node {n_name}',
      f_status='SKIPPED',
      topology=topology)
    TEST_COUNT.skip += 1                        # Increment skip count for test results summary
    return (True,None)                          # Processed, unknown result

  if args.verbose >= 2:                         # Print out what will be executed
    cmd = utils.get_entry_value(v_entry,action,node,topology)
    print(f'{action} on {node.name}/{node.device}: {cmd}')

  OK = None
  if action == 'show':                          # We got a 'show' action, try to get parsed results
    result = devices.get_parsed_result(v_entry,n_name,topology,args.verbose)
    if '_error' in result:                      # OOPS, we failed (unrecoverable)
      report.increase_fail_count(v_entry)
      return (True, False)                      # ... and return (processed, failed)
  elif action == 'exec':                        # We got an 'exec' action, try to get something out of the device
    result.stdout = devices.get_result_string(v_entry,n_name,topology,report_error)
    if result.stdout is False:                  # Did the exec command fail?
      if report_error:
        report.increase_fail_count(v_entry)
        return (True, False)                    # Return (processed, failed)
  elif action == 'suzieq':
    result = suzieq.get_result(v_entry,n_name,topology,args.verbose)
    OK = bool(result) != (v_entry.suzieq.get('expect','data') == 'empty')
    if not OK and report_error:
      report.p_test_fail(n_name,v_entry,topology,'suzieq did not return the expected data')
      report.increase_fail_count(v_entry)
      return(True,False)

  if OK != False and 'valid' in v_entry:        # Do we have a validation expression in the test entry?
    if action == 'suzieq':
      OK = suzieq.execute_validation(v_entry,node,topology,result,args.verbose,report_error)
    else:
      OK = utils.execute_validation_expression(v_entry,node,topology,result,args.verbose,report_error)
  elif 'plugin' in v_entry:                     # If not, try to call the plugin function
    OK = plugin.execute_validation_plugin(v_entry,node,topology,result,args.verbose,report_error)
  elif OK != False and 'pass' in v_entry:
    report.log_progress(f"{node.name}: {v_entry['pass']}",topology)

  if OK is False:                               # Validation failed...
    if not report_error:                        # ... but we still don't have to report it?
      return (False, None)                      # ... return (not processed, unknown)
    if 'result' in args.dump:                   # Do we have to dump the result for further troubleshooting?
      if isinstance(result,Box):                # If the result is a Box, clean it first
        for kw in ['re']:                       # ... remove extra keys first
          result.pop(kw,None)
        # ... and remove the 'result' key if it's not needed
        if 'result' in result and isinstance(result.result,Box):
          result.pop('result',None)
      print(f'Returned result\n{"=" * 80}\n{result.to_yaml()}')

  return (True, OK)                             # ... otherwise return (processed, validation result)

'''
Execute a single validation test on all specified nodes
'''
def execute_validation_test(
      v_entry: Box,
      topology: Box,
      start_time: typing.Optional[typing.Union[int,float]],
      args: argparse.Namespace) -> typing.Optional[bool]:
  from . import TEST_COUNT

  # Return value uses ternary logic: OK (True), Fail(False), Skipped (None)
  ret_value = None

  report.p_test_header(v_entry,topology)          # Print test header
  if 'wait' in v_entry and not v_entry.nodes:     # Handle pure wait case
    if v_entry.get('stop_on_error',False):
      if TEST_COUNT.failed:
        report.log_failure('Validation failed due to previous errors',topology)
        sys.exit(1)
      else:
        report.log_info(v_entry.get('pass','No errors so far, moving on'),topology)

    if v_entry.get('level',None) == 'warning':    # Warning-generating placeholder
      report.increase_fail_count(v_entry)         # ... used with test-modifying plugins
      report.p_test_fail('',v_entry,topology)     # Simulate a failure, the rest will follow ;)
      return False

    if not args.nowait and v_entry.wait:
      wait_before_testing(v_entry,start_time,topology)
    return None

  if not v_entry.nodes:
    report.log_info(
      f'There are no nodes specified for this test, skipping...',
      f_status='SKIPPED',
      topology=topology)
    TEST_COUNT.skip += 1
    return None

  if 'config' in v_entry:
    return devices.execute_netlab_config(v_entry,topology)

  wait_time = 0 if args.nowait else v_entry.get('wait',0)
  start_time= time.time()
  stop_time = start_time + wait_time              # Time to wait for successful result
  wait_msg  = v_entry.get('wait_msg',None)        # Message to display if starting sleep after the first try
  wait_time = time.time()                         # Time to display first 'waiting' message
  wait_cnt  = 0                                   # How many 'waiting' messages did we display?
  n_remaining: list = v_entry.nodes               # Start with all nodes specified in the validation entry

  while n_remaining:                              # Keep retrying 
    for n_name in n_remaining:                    # Iterate over remaining nodes
      (proc,OK) = execute_node_validation(v_entry,topology,n_name,time.time() >= stop_time,args)
      if proc:                                    # Have we processed this node? Remove node from remaining list
        n_remaining = [ x for x in n_remaining if x != n_name ]

      # The result could be 'True', 'False', or 'None' (don't know)
      if OK is True and ret_value is None:        # If we have a True result and we don't know the composite result yet
        ret_value = True                          # ... set composite result to True
      elif OK is False:                           # But if we have a single failure ...
        ret_value = False                         # ... set composite result to False (failure)

    if ret_value is not False and n_remaining and wait_msg:
      if wait_time < time.time():
        if 'wait' in v_entry and wait_cnt == 0:
          extra_msg = f' (retrying for {v_entry.wait} seconds)'
        else:
          extra_msg = f' ({int(stop_time - time.time())} seconds left)'
        report.log_info(
          wait_msg + extra_msg,
          f_status = 'WAITING',
          topology=topology)
        wait_cnt += 1                             # Next message will be X seconds left
        wait_time += 15                           # ... and it will happen after 15 seconds
      time.sleep(1)

  if ret_value:                                   # If we got to 'True'
    report.log_info(
      f'Test succeeded in { round(time.time() - start_time,1) } seconds',
      f_status = 'PASS',
      f_color= 'light_green',
      topology=topology)
    if 'pass' in v_entry:
      report.p_test_pass(v_entry,topology)        # ... declare Mission Accomplished

  return ret_value
