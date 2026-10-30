#
# netlab initial -- implement standard device readiness checks
#
import concurrent.futures
import subprocess
import threading
import time
import typing

from box import Box

from ....augment import devices as a_devices
from ....utils import log, netmiko, strings
from ... import error_and_exit
from .utils import PRINT_LOCK, check_sshpass, set_timeouts, status_display

"""
Prepare for SSH readiness check -- copy timeouts and retry counters, check for "sshpass", set up the SSH command
"""
SSH_PROVIDER_TIMEOUT_INFO: dict = {}

def setup_ssh_ready_parameters(nodeset: list, topology: Box) -> None:
  global SSH_PROVIDER_TIMEOUT_INFO

  def get_show_command(n_data: Box, netmiko: bool = False) -> str:
    if netmiko:
      features = a_devices.get_device_features(n_data,defaults)
      if 'netmiko.ssh_ready.command' in features:
        return features.netmiko.ssh_ready.command

    return a_devices.get_node_group_var(n_data,'netlab_check_command',defaults) or 'show version'

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
    ssh_cmd = get_show_command(n_data)
    ssh_exec.append(ssh_cmd)
    if log.debug_active('ssh'):
      print(f'SSH cmd for {n_data.name}: {" ".join(ssh_exec)}')
    return ssh_exec

  defaults = topology.defaults

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    r_data = n_data._ready

    set_timeouts(n_data,defaults)
    n_provider = a_devices.get_provider(n_data,defaults)
    features = a_devices.get_device_features(n_data,defaults)
    p_wait = defaults.providers[n_provider].get('ssh_timeout',r_data.wait)
    if p_wait > r_data.wait:
      r_data.wait = p_wait
      if n_provider not in SSH_PROVIDER_TIMEOUT_INFO:
        log.info(f'Minimum SSH timeout extended to {p_wait} seconds',module=n_provider)
        SSH_PROVIDER_TIMEOUT_INFO[n_provider] = True

    if log.debug_active('ssh'):
      print(f'SSH wait times for {n_data.name}: delay={r_data.delay}, retries={r_data.retries}')

    if netmiko.NETMIKO_IS_MISSING:
      if features.get('netmiko.required',False):
        log.error(
          f'Node {n_name}/device {n_data.device} needs Netmiko to check its SSH server',
          category=log.MissingDependency,
          module='initial',
          more_hints='use "netlab install netmiko" to install Netmiko and Paramiko libraries')
    elif features.get('netmiko.device_type',None):
      params = netmiko.prepare_params(n_data,topology,quiet=True)
      if params:                                            # Use netmiko only if we know it works
        for kw in ('conn_timeout','banner_timeout','auth_timeout','read_timeout_override'):
          params[kw] = r_data.delay                         # Adjust all known netmiko timeouts
        r_data.netmiko_params = params
        r_data.netmiko_command = get_show_command(n_data,netmiko=True)
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

  def probe_ssh(n_name: str, n_data: Box, r_data: Box) -> bool:
    if log.debug_active('ssh'):
      print(f'SSH: starting check on {n_name}, timeout={r_data.delay}',flush=True)
    subprocess.run(args=r_data.ssh_exec,capture_output=True,check=True,timeout=r_data.delay)
    r_data.ssh_ready = True                               # No errors, we're ready to roll
    now = time.time()
    if now > start_time + 5 or log.VERBOSE:               # Report progress only if it's worth reporting
      with PRINT_LOCK:
        strings.print_colored_text('[SSH]     ','green')
        print(f'SSH server on node {n_name} (device {n_data.device}) ' +\
              f'is ready after {round(now - start_time,1)} seconds',flush=True)
    return True

  def probe_netmiko(n_name: str, n_data: Box, r_data: Box) -> bool:
    """
    netmiko-based SSH probe
    """
    if log.debug_active('ssh'):
      print(f'netmiko: starting check on {n_name}, command={r_data.netmiko_command}, timeout={r_data.delay}',flush=True)
    conn = netmiko.connect(n_data,r_data.netmiko_params,quiet=True)
    if not conn:
      return False
    with conn:
      if r_data.netmiko_command:
        if not conn.send_command(r_data.netmiko_command):
          return False

    r_data.ssh_ready = True                               # No errors, we're ready to roll
    now = time.time()
    if now > start_time + 5 or log.VERBOSE:               # Report progress only if it's worth reporting
      with PRINT_LOCK:
        strings.print_colored_text('[SSH]     ','green')
        print(f'netmiko reports node {n_name} (device {n_data.device}) is ready for SSH ' +\
              f'after {round(now - start_time,1)} seconds',flush=True)
    return True

  def wait_for_ssh(n_name: str) -> bool:                    # Try out SSH server on the device
    n_data = topology.nodes[n_name]
    r_data = n_data._ready                                  # Get device ready data
    result = ''
    try:                                                    # Try the SSH command
      if 'netmiko_command' in r_data:
        if probe_netmiko(n_name,n_data,r_data):
          return True
      else:
        if probe_ssh(n_name,n_data,r_data):
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
        with PRINT_LOCK:
          strings.print_colored_text('[SSH]     ','red')
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
  setup_ssh_ready_parameters(waitset,topology)
  log.exit_on_error()

  # If at least one node cannot use netmiko, we must check for sshpass command
  if any('netmiko_command' not in topology.nodes[n_name]._ready for n_name in waitset):
    check_sshpass()

  start_time = time.time()
  stop_display = threading.Event()
  log.info(text=f'Checking SSH server(s) on {",".join(waitset)}')

  with concurrent.futures.ThreadPoolExecutor() as executor:
    if strings.rich_color:
      executor.submit(status_display,devices_not_ready,'[SSH] ','ssh',start_time,stop_display)
    try:
      while True:
        check_list = devices_not_ready()
        if not check_list:
          break
        for result in executor.map(wait_for_ssh, check_list):
          pass
        time.sleep(1)                             # Wait a bit before running another iteration
    finally:
      stop_display.set()                          # Stop the status display even when we're bailing out

  failed_list = [ n_name for n_name in waitset if topology.nodes[n_name]._ready.ssh_failed ]
  if failed_list:
    error_and_exit(
      f'SSH server did not start in time on node(s) {",".join(failed_list)}',
      doc_url='netlab/initial/#netlab-initial-ready')
