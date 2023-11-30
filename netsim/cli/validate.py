#
# netlab validate command
#
# Perform lab validation tests
#
import typing
import os
import sys
import argparse

from box import Box
from termcolor import colored

from . import load_snapshot,parser_add_debug,parser_add_verbose
from ..utils import log,templates
from .. import data
from .connect import connect_to_node,LogLevel

#
# CLI parser for 'netlab validate' command
#
def validate_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in transformed lab topology')
  parser_add_debug(parser)                                # Add debugging options
  parser_add_verbose(parser)                              # ... and verbosity flag
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
#  parser.add_argument(
#    '--node',
#    dest='node', action='store',
#    help='Execute validation tests only on selected node')
#  parser.add_argument(
#    dest='tests', action='store',
#    nargs='?',
#    help='Validation test(s) to execute (default: all)')

  return parser.parse_args(args)

# The following routines print colored test status and offer
# various levels of abstraction, from "give me a colored text"
# to "tell the user the lab was a great success"

# Prepare test status (colored text in fixed width)
#
def p_status(txt: str, color: str, topology: Box) -> str:
  txt = f'[{txt}]{" " * 80}'[:topology._v_len+3]
  return colored(txt,color)

# Print test header
#
def p_test_header(v_entry: Box,topology: Box) -> None:
  print(
    p_status(v_entry.name,"light_cyan",topology) + \
    v_entry.get('description','Starting test') + \
    f' [ node(s): {",".join(v_entry.nodes)} ]')

# Print generic "test failed" message
#
def log_failure(msg: str, topology: Box, f_status: str = 'FAIL') -> None:
  print(p_status(f_status,'light_red',topology) + msg)

# Print generic "making progress" message
#
def log_progress(msg: str, topology: Box, f_status: str = 'PASS') -> None:
  print(p_status(f_status,'light_green',topology) + msg)

# Print generic "ambivalent info" message
#
def log_info(msg: str, topology: Box, f_status: str = 'INFO') -> None:
  print(p_status(f_status,'yellow',topology) + msg)

# Print "test failed on node"
#
def p_test_fail(n_name: str, v_entry: Box, topology: Box) -> None:
  err = v_entry.get('fail','')
  err = f'Node {n_name}: '+err if err else f'Test failed for node {n_name}'
  log_failure(err,topology)

# Print "test passed"
#
def p_test_pass(v_entry: Box, topology: Box) -> None:
  msg = v_entry.get('pass','Test succeeded')
  log_progress(msg,topology)

# Print "all tests succeeded"
#
def p_success(topology: Box) -> None:
  print()
  log_progress('All tests passed',topology,f_status='SUCCESS')

'''
Get generic or per-device action from a validation entry

* If the validation entry is a string, use that
* If the validation entry is a dictionary, use device-specific item
* If the result of the above is not a string we have a failure, get out
* If the resulting string contains '{{' run it through Jinja2 engine
'''
def get_entry_value(v_entry: Box, action: str, node: Box) -> typing.Any:
  n_device = node.device
  value = v_entry[action][n_device] if isinstance(v_entry[action],dict) else v_entry[action]
  if not isinstance(value,str):
    return value
  
  if '{{' in value:
    value = templates.render_template(data=node,j2_text=value)
#    print(f"{action} value for {node.name}: {value}")

  return value  

'''
Get the command to execute on the device in list format

* Use 'get_entry_value' to get the action string or list
* If we got a string, transform it into a list
'''
def get_exec_list(v_entry: Box, action: str, node: Box) -> list:
  v_cmd = get_entry_value(v_entry,action,node)
  if isinstance(v_cmd,list):
    return v_cmd
  elif isinstance(v_cmd,str):
    return v_cmd.split(' ')

  return []

'''
Execute a 'show' command. The return value is expected to be parseable JSON
'''
def get_parsed_result(v_entry: Box, n_name: str, topology: Box) -> Box:
  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = get_exec_list(v_entry,'show',node)                # ... and the 'show' action for the current node
  err_value = data.get_box({'_error': True})                # Assume an error

  if not v_cmd:                                             # We should not get here, but we could...
    log.error(
      f'Test {v_entry.name}: have no idea what show command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation')
    return err_value

  # Set up arguments for the 'netlab connect' command and execute it
  #
  args = argparse.Namespace(quiet=True,host=n_name,output=True,show=v_cmd)
  result = connect_to_node(args=args,rest=[],topology=topology,log_level=LogLevel.NONE)

  # If the result we got back is not a string, the 'netlab connect' command
  # failed in one way or another
  #
  if not isinstance(result,str):
    log_failure(
      f'Failed to execute show command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',
      topology=topology)
    return err_value

  # Try to parse the results we got back as JSON data
  #
  try:
    return Box.from_json(result)
  except:
    log_failure(
      f'Failed to parse result output of "{" ".join(v_cmd)}" on {n_name} (device {node.device}) as JSON',
      topology=topology)
    return err_value

'''
Execute a command on the device and return stdout
'''
def get_result_string(v_entry: Box, n_name: str, topology: Box) -> typing.Union[bool,str]:
  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = get_exec_list(v_entry,'exec',node)                # ... and the 'exec' action for the current node
  if not v_cmd:                                             # We should not get here, but we could...
    log.error(
      f'Test {v_entry.name}: have no idea what command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation')
    return False

  # Set up arguments for the 'netlab connect' command and execute it
  #
  args = argparse.Namespace(quiet=True,host=n_name,output=True)
  result = connect_to_node(args=args,rest=v_cmd,topology=topology,log_level=LogLevel.NONE)

  if result is False:                                       # Report an error if 'netlab connect' failed
    log_failure(
      f'Failed to execute command {v_cmd} on {n_name} (device {node.device})',topology)

  return result

'''
find_test_action -- find something that can be executed on current node

* Try 'show' and 'exec' actions
* If an action value is a string, the user doesn't care about multi-vendor
  setup. Run with whatever the user specified
* If the user specified a multi-vendor setup, try to use the device-specific
  action
* If everything fails, return None (nothing usable for the current node)
'''
def find_test_action(v_entry: Box, node: Box) -> typing.Optional[str]:
  for kw in ('show','exec'):
    if not kw in v_entry:
      continue
    if isinstance(v_entry[kw],str):
      return kw
    if node.device in v_entry[kw]:
      return kw

  return None

test_skip_count: int

'''
Execute a single validation test on all specified nodes
'''
def execute_validation_test(v_entry: Box,topology: Box, args: argparse.Namespace) -> typing.Optional[bool]:
  global test_skip_count

  # Return value uses ternary logic: OK (True), Fail(False), Skipped (None)
  ret_value = None

  p_test_header(v_entry,topology)                 # Print test header
  for n_name in v_entry.nodes:                    # Iterate over all specified nodes
    node = topology.nodes[n_name]
    result = data.get_empty_box()

    action = find_test_action(v_entry,node)       # Find the action to show/execute
    if action is None:                            # None found, skip this node
      log_info(
        f'Test action not defined for device {node.device} / node {n_name}',
        f_status = 'SKIPPED',
        topology=topology)
      test_skip_count += 1                        # Increment skip count for test results summary
      continue

    if action == 'show':                          # We got a 'show' action, try to get parsed results
      result = get_parsed_result(v_entry,n_name,topology)
      if '_error' in result:                      # OOPS, we failed
        ret_value = False
        continue
    elif action == 'exec':                        # We got an 'exec' action, try to get something out of the device
      result.stdout = get_result_string(v_entry,n_name,topology)
      if result.stdout is False:                  # Store device printout in 'stdout'
        ret_value = False
        continue

    if 'valid' in v_entry:                        # Do we have a validation expression in the test entry?
      v_test = get_entry_value(v_entry,'valid',node)
      if not v_test:                              # Do we have a validation expression for the current device?
        log_info(                                 # ... nope, have to skip it
          f'Test results validation not defined for device {node.device} / node {n_name}',
          f_status = 'SKIPPED',
          topology=topology)
        test_skip_count += 1
        OK = None
      else:
        try:                                      # Otherwise try to evaluate the validation expression
          OK = eval(v_test,{'__builtins': {}},result)
        except:                                   # ... and failure if the evaluation failed
          OK = False

      if not OK:                                  # Validation expression failed...
        if args.verbose > 0:
          if v_test:
            print(f'Test expression: {v_test}\n')
            print(f'Evaluated result {OK}')
          print(f'Result received from {n_name}\n{"-" * 80}\n{result.to_json()}\n')

      if OK is not None and not OK:               # We have a real result (not skipped) that is not OK
        p_test_fail(n_name,v_entry,topology)
        ret_value = False
      elif OK:                                    # ... or we might have a positive result
        log_progress(f'Validation succeeded on {n_name}',topology)
        if ret_value is None:
          ret_value = True

  if ret_value:                                   # If we got to 'True'
    p_test_pass(v_entry,topology)                 # ... declare Mission Accomplished

  return ret_value

'''
Main routine: run all tests, handle validation errors, print summary results
'''
def run(cli_args: typing.List[str]) -> None:
  global test_skip_count
  args = validate_parse(cli_args)
  topology = load_snapshot(args)

  if 'validate' not in topology:
    log.fatal('No validation tests defined for the current lab, exiting')

  status = True
  cnt = 0
  test_skip_count = 0
  topology._v_len = max([ len(v_entry.name) for v_entry in topology.validate ] + [ 7 ])

  for v_entry in topology.validate:
    if cnt:
      print()

    result = execute_validation_test(v_entry,topology,args)
    if result is False:
      status = False
      if v_entry.stop_on_error:
        print()
        log_failure('Mandatory test failed, validation stopped',topology)
        sys.exit(1)

    cnt = cnt + 1

  if status:
    p_success(topology)
    if test_skip_count:
      log_info('Some tests were skipped, the results are not reliable',topology)
  else:
    print()
    log_failure('Tests completed, validation failed',topology)

  sys.exit(0 if status else 1)
