#
# netlab initial -- implement standard device readiness checks
#
import concurrent.futures
import subprocess
import time
import typing

from box import Box

from ...augment import devices as a_devices
from ...data import append_to_list, get_empty_box
from ...utils import log, strings
from .. import error_and_exit, external_commands

"""
Prepare for SSH readiness check -- copy timeouts and retry counters, check for "sshpass", set up the SSH command
"""
def setup_ssh_ready_parameters(nodeset: list, topology: Box) -> None:

  # Get a group variable (if it's an int) or a default
  #
  def get_int_var_value(n_data: Box, var: str, def_val: int) -> int:
    result = a_devices.get_node_group_var(n_data,var,defaults)
    return result if isinstance(result,int) else def_val

  # Build SSH command
  #
  def build_ssh_command(n_data: Box) -> typing.Optional[list]:
    ssh_pass = a_devices.get_node_group_var(n_data,'ansible_ssh_pass',defaults)
    ssh_exec = ['sshpass','-p',ssh_pass] if ssh_pass else []
    ssh_exec.extend(['ssh','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null'])
    ssh_args = a_devices.get_node_group_var(n_data,'netlab_ssh_args',defaults)
    if ssh_args:
      ssh_exec += ssh_args.split(' ')
    ssh_host = n_data.get('mgmt.ipv4',None) or n_data.get('mgmt.ipv6',None)
    if not ssh_host:
      log.error(
        f'Cannot check the SSH server on node {n_data.name} (device {n_data.device})',
        more_hints=['The node does not have a management IPv4 or IPv6 address'],
        category=log.MissingValue,
        module='initial')
      return None
    ssh_dest = a_devices.get_node_group_var(n_data,'ansible_user',defaults) + "@" + str(ssh_host)
    ssh_exec.append(ssh_dest)
    ssh_cmd = a_devices.get_node_group_var(n_data,'netlab_check_command',defaults) or "show version"
    ssh_exec.append(ssh_cmd)
    if log.debug_active('ssh'):
      print(f'SSH cmd for {n_data.name}: {" ".join(ssh_exec)}')
    return ssh_exec

  defaults = topology.defaults

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    r_data = n_data._ready
    r_data.retries = get_int_var_value(n_data,'netlab_check_retries',20)  # Get sane retries
    r_data.delay   = get_int_var_value(n_data,'netlab_check_delay',5)     # ... and delay values
    r_data.wait    = r_data.retries * r_data.delay                        # ... and calculate total wait time
    if log.debug_active('ssh'):
      print(f'SSH wait times for {n_data.name}: delay={r_data.delay}, retries={r_data.retries}')
    r_data.ssh_exec = build_ssh_command(n_data)             # Get the SSH command to execute
    r_data.ssh_ready = False                                # ... and assume the device is not ready
    r_data.ssh_failed = False                               # ... but also hasn't failed yet

def device_ssh_ready(waitset: list, topology: Box) -> None:

  def devices_not_ready() -> list:                          # Get the list of devices that are still not ready
    wait_list = []
    for n_name in waitset:
      n_data = topology.nodes[n_name]
      if n_data._ready.ssh_exec and not n_data._ready.ssh_ready and not n_data._ready.ssh_failed:
        wait_list.append(n_name)                            # Device is still not ready (but has not failed yet)
    return wait_list  

  def status_display() -> None:                             # Display status every second
    while True:                                             # Iterate until everything is done
      wait_list = devices_not_ready()                       # Get the list of not-ready devices
      if not wait_list:                                     # All done?
        return                                              # ... let's get out of here

      strings.print_colored_text('[SSH] ','green')
      w_time = round(time.time() - start_time,1)
      print(
        f'Waiting for {len(wait_list)} devices ({w_time} seconds)',
        end='\n' if log.debug_active('ssh') else '\r',flush=True)
      time.sleep(1)

  def wait_for_ssh(n_name: str) -> bool:                    # Try out SSH server on the device
    n_data = topology.nodes[n_name]
    r_data = n_data._ready                                  # Get device ready data
    result = ''
    try:                                                    # Try the SSH command
      if log.debug_active('ssh'):
        print(f'SSH: starting check on {n_name}, timeout={r_data.delay}',flush=True)
      subprocess.run(args=r_data.ssh_exec,capture_output=True,check=True,timeout=r_data.delay)
      r_data.ssh_ready = True                               # No errors, we're ready to roll
      now = time.time()
      if now > start_time + 5 or log.VERBOSE:               # Report progress only if it's worth reporting
        strings.print_colored_text('[SSH] ','green')
        print(f'SSH server on node {n_name} (device {n_data.device}) ' +\
              f'is ready after {round(now - start_time,1)} seconds',flush=True)
      return True
    except subprocess.CalledProcessError as ex:             # SSH reported an error
      result = str(ex)
    except subprocess.TimeoutExpired as ex:                 # SSH got stuck
      result = f'Timeout: '+str(ex)
    except Exception as ex:                                 # Or it could be anything else
      result = str(ex)

    try:
      now = time.time()
      if now > start_time + r_data.wait:                    # Have we exceeded the wait period?
        r_data.ssh_failed = True
        strings.print_colored_text('[SSH] ','red')
        print(f'SSH server on node {n_name} (device {n_data.device}) ' +\
              f'is not ready after {round(now - start_time,1)} seconds',flush=True)
      if log.debug_active('ssh'):                         # Do we need to report SSH status periodically?
        if now > r_data.get('debug_time',start_time) + 5:   # Report errors only every five seconds
          print(f'SSH: Error on {n_data.name} ({n_data.device}): {result}')
          r_data.debug_time = now                           # Remember the last time we reported an error
    except Exception as ex:
      print(f'ERROR in wait_for_ssh: {str(ex)}')

    return False

  # Start of device_ssh_ready main code
  if not external_commands.has_command('sshpass'):
    error_and_exit(
      f'sshpass command is not installed',
      more_hints=['netlab initial needs "sshpass" to check SSH readiness of lab devices'],
      category=log.MissingDependency)

  setup_ssh_ready_parameters(waitset,topology)
  log.exit_on_error()
  start_time = time.time()
  log.info(text=f'Checking SSH servers on {",".join(waitset)}')

  with concurrent.futures.ThreadPoolExecutor() as executor:
    if strings.rich_color:
      executor.submit(status_display)
    while True:
      check_list = devices_not_ready()
      if not check_list:
        break
      for result in executor.map(wait_for_ssh, check_list):
        pass
      time.sleep(1)                               # Wait a bit before running another iteration

  failed_list = [ n_name for n_name in waitset if topology.nodes[n_name]._ready.ssh_failed ]
  if failed_list:
    error_and_exit(f'SSH server did not start in time on node(s) {",".join(failed_list)}')

READY_ACTIONS = { 'ssh': device_ssh_ready }

"""
Execute all "wait for device to be ready" steps recognized by "netlab initial". Further
steps might have to be executed by Ansible playbooks
"""
def device_ready(nodeset: list, topology: Box) -> None:
  global READY_ACTIONS
  waitlists = get_empty_box()
  defaults = topology.defaults

  # Build lists of device requiring a specific ready step
  #
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    ready_steps = a_devices.get_node_group_var(n_data,'netlab_ready',defaults)
    if not isinstance(ready_steps,list):
      continue
    for step in ready_steps:
      append_to_list(waitlists,step,n_name)

  # Iterate over known steps, check whether any device needs that, and execute
  # the corresponding ready function
  for r_step in READY_ACTIONS.keys():
    if r_step not in waitlists:                   # Nobody asked for this step, move on
      continue
    READY_ACTIONS[r_step](waitlists[r_step],topology)
