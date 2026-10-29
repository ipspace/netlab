#
# netlab initial -- implement standard device readiness checks
#
import argparse
import concurrent.futures
import re
import time

from box import Box

from ....augment import devices as a_devices
from ....utils import log, strings
from ... import error_and_exit
from ...connect import LogLevel, connect_to_node
from .utils import PRINT_LOCK, check_sshpass, set_timeouts


def setup_command_parameters(nodeset: list, topology: Box) -> None:
  """
  Set up node _ready parameters for "wait for command results" readiness check
  """
  defaults = topology.defaults

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    features = a_devices.get_device_features(n_data,defaults)
    c_ready = features.get('command.ready',None)
    if not c_ready:
      log.fatal(f'Internal error: node {n_name}/device {n_data.device} does not have command.ready features defined')

    c_vars = dict(n_data)                                   # Variables available to 'when' and 'expect'
    c_vars['phy_interfaces'] = [ intf for intf in n_data.interfaces if 'virtual_interface' not in intf ]

    if 'when' in c_ready:
      need_check = eval(c_ready.when,{},c_vars)
      if not need_check:
        continue

    r_data = set_timeouts(n_data,defaults)
    for kw in ('execute','expect'):
      if kw not in c_ready:
        log.fatal(f'Internal error: device {n_data.device} is missing features.command.ready.{kw} setting')
      r_data.command[kw] =  strings.eval_format(c_ready[kw],c_vars)

    # Check whether we need sshpass to access the device
    conn = a_devices.get_node_group_var(n_data,'netlab_console_connection',defaults) or \
           a_devices.get_node_group_var(n_data,'ansible_connection',defaults)
    r_data.command.sshpass = conn != 'docker' and \
                             bool(a_devices.get_node_group_var(n_data,'ansible_ssh_pass',defaults))

    if log.debug_active('ready'):
      print(f'Command wait times for {n_data.name}: delay={r_data.delay}, retries={r_data.retries}')

def device_command_ready(waitset: list, topology: Box) -> None:

  def devices_not_ready() -> list:                          # Get the list of devices that are still not ready
    wait_list = []
    for n_name in waitset:
      n_data = topology.nodes[n_name]
      if 'command.status' not in n_data._ready:
        wait_list.append(n_name)                            # Device is still not ready (but has not failed yet)
    return wait_list

  def status_display() -> None:                             # Display status every second
    while True:                                             # Iterate until everything is done
      wait_list = devices_not_ready()                       # Get the list of not-ready devices
      if not wait_list:                                     # All done?
        return                                              # ... let's get out of here

      with PRINT_LOCK:
        strings.print_colored_text('[READY]   ','green')
        w_time = round(time.time() - start_time,1)
        print(
          f'Waiting for {len(wait_list)} devices ({w_time} seconds)',
          end='\n' if log.debug_active('ready') else '\r',flush=True)
      time.sleep(1)

  def wait_for_command(n_name: str) -> bool:
    """
    Check whether a command executed on the device returns expected results
    """
    n_data = topology.nodes[n_name]
    r_data = n_data._ready                                  # Get device ready data
    args = argparse.Namespace(quiet=True,output=True,show=None,verbose=False,timeout=r_data.delay)
    now = time.time()
    try:                                                    # Try the SSH command
      expect = strings.eval_format(r_data.command.expect,n_data)
      log_level = LogLevel.INFO if log.debug_active('ready') else LogLevel.NONE
      result = connect_to_node(node=n_name,args=args,rest=[ r_data.command.execute ],topology=topology,log_level=log_level)

      if log.debug_active('ready'):
        print(f'Expecting {expect}, result: {result}')
      if isinstance(result,str) and re.search(expect,result):
        r_data.command.status = True
        if now > start_time + 5 or log.VERBOSE:               # Report progress only if it's worth reporting
          with PRINT_LOCK:
            strings.print_colored_text('[READY]   ','green')
            print(f'Node {n_name} (device {n_data.device}) ' +\
                  f'is ready after {round(now - start_time,1)} seconds',flush=True)
        return True
    except Exception as ex:                                 # Catch all exceptions
      r_data.command.status = False
      result = str(ex)

    try:
      if now > start_time + r_data.wait:                    # Have we exceeded the wait period?
        r_data.command.status = False
        with PRINT_LOCK:
          strings.print_colored_text('[READY]   ','red')
          print(f'Node {n_name} (device {n_data.device}) ' +\
                f'is not ready after {round(now - start_time,1)} seconds',flush=True)
      if log.debug_active('ready'):                         # Do we need to report SSH status periodically?
        if now > r_data.get('debug_time',start_time) + 5:   # Report errors only every five seconds
          print(f'READY: {n_data.name} ({n_data.device}): {result}')
          r_data.debug_time = now                           # Remember the last time we reported an error
    except Exception as ex:
      print(f'ERROR in wait_for_command: {str(ex)}')

    return False

  setup_command_parameters(waitset,topology)
  waitset = [ n_name for n_name in waitset if '_ready.command' in topology.nodes[n_name]]
  if not waitset:
    return

  if any(topology.nodes[n_name]._ready.command.sshpass for n_name in waitset):
    check_sshpass()

  start_time = time.time()
  log.info(text=f'Verifying the lab devices are ready: {",".join(waitset)}')

  with concurrent.futures.ThreadPoolExecutor() as executor:
    if strings.rich_color:
      executor.submit(status_display)
    while True:
      check_list = devices_not_ready()
      if not check_list:
        break
      for _ in executor.map(wait_for_command, check_list):
        pass
      time.sleep(1)                               # Wait a bit before running another iteration

  failed_list = [ n_name for n_name in waitset if topology.nodes[n_name]._ready.get('command.status',None) is False ]
  if failed_list:
    error_and_exit(
      f'These lab devices are still not ready to be used: {",".join(failed_list)}',
      doc_url='netlab/initial/#netlab-initial-ready')
