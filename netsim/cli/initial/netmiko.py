"""
Use netmiko instead of Ansible to deploy device configurations

* send_config: send configuration commands to the device over a SSH session
* send_script: copy configuration script to the device with SCP and execute it
"""
import os
import time

from box import Box

from ...augment import devices as a_devices
from ...data import append_to_list
from ...providers import PRINT_LOCK
from ...utils import log, strings
from ...utils import netmiko as _netmiko
from ...utils import templates as _templates


def send_config(
      net_connect: '_netmiko._netmiko.BaseConnection',
      n_data: Box,
      cfg_item: str,
      cfg_file: str,
      features: Box,
      netmiko_errors: str) -> bool:
  """
  Send configuration commands from the config file to the device. Raises an exception on failure
  """
  cfg_result = net_connect.send_config_from_file(cfg_file,error_pattern=netmiko_errors)
  log.info(f'Sent {cfg_item} configuration to {n_data.name}',module='netmiko')
  if _netmiko.has_commit(net_connect):
    cfg_result += net_connect.commit()
  if features.get('netmiko.config.always_exit',False):
    cfg_result += net_connect.exit_config_mode()
  if log.debug_active('netmiko'):
    print(f'Config {cfg_item} on {n_data.name}:\n{cfg_result}')
  if cfg_item in ['normalize','initial']:
    net_connect.set_base_prompt()

  return True

def send_script(
      net_connect: '_netmiko._netmiko.BaseConnection',
      n_data: Box,
      cfg_item: str,
      cfg_file: str,
      features: Box) -> bool:
  """
  Copy the configuration script to the device and execute it over a separate SSH channel.
  Reports errors and returns False on failure
  """
  cfg_dir = features.get('netmiko.config.directory','/tmp').rstrip('/')
  dst_file = f"{cfg_dir}/netlab-{cfg_item.replace('/','_')}.sh"
  if not _netmiko.scp(net_connect,n_data.name,cfg_file,dst_file):
    return False

  become = features.get('netmiko.config.become',False)      # Mirror Ansible: True => sudo, string => verbatim
  timeout = features.get('netmiko.config.timeout',30)
  use_session = bool(net_connect.secret)
  if use_session:
    # We have the sudo password (ansible_become_password), and netmiko used it to get a root
    # shell (enable) in the interactive session. Execute the script in that session; we cannot
    # respond to the sudo password prompt on a separate SSH channel
    #
    pfx = f'{become} ' if isinstance(become,str) else ''
  else:
    # Use 'sudo -n' to fail instead of hanging on a sudo password prompt
    #
    pfx = 'sudo -n ' if become is True else f'{become} ' if become else ''

  cmd = f'chmod a+x {dst_file}; {pfx}{dst_file}'
  if use_session:
    result = _netmiko.command(net_connect,n_data.name,cmd,timeout=timeout)
  else:
    # Execute the script in a PTY (like Ansible does). Without it, daemons started by the
    # script (for example, FRR daemons) keep the SSH channel open after the script exits
    #
    result = _netmiko.execute(net_connect,n_data.name,cmd,get_pty=True,timeout=timeout)

  if result is None:                                        # SSH error or timeout, already reported
    return False

  (output,errors,rc) = result
  if log.debug_active('netmiko'):
    print(f'Config {cfg_item} on {n_data.name} (rc={rc}):\n{output}{errors}')

  if rc == 0:
    log.info(f'Executed {cfg_item} configuration script on {n_data.name}',module='netmiko')
    if log.VERBOSE and output:                              # Print the script outputs in verbose mode
      with PRINT_LOCK:
        log.info(f'Results of executing {cfg_item} configuration on {n_data.name}')
        strings.print_colored_text(txt=output,color='green')
    return True

  with PRINT_LOCK:
    log.error(
      f'{cfg_item} configuration script failed on {n_data.name} (exit code {rc})',
      category=log.FatalError,
      skip_header=True,
      module='netmiko')
    if output or errors:                                    # Print script outputs when available
      strings.print_colored_text(txt=output+errors,color='bright_black')

  return False

def deploy(n_data: Box,topology: Box,n_deploy: list) -> None:
  node_config = n_data.get('_node_config',None)
  if not node_config:
    return

  if not _netmiko.check_netmiko(n_data):
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return

  netmiko_params = _netmiko.prepare_params(n_data,topology)
  if not netmiko_params:
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return None

  net_connect = _netmiko.connect(n_data,netmiko_params)
  if not net_connect:
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return

  session_log = netmiko_params["session_log"]
  features = a_devices.get_device_features(n_data,topology.defaults)
  use_script = _templates.config_is_script('netmiko',n_data,topology.defaults)

  netmiko_delay = features.get('netmiko.config.delay',None)
  if netmiko_delay:
    time.sleep(netmiko_delay)

  netmiko_err_list = features.get('netmiko.error_regexp',None)
  netmiko_errors = rf"({'|'.join(netmiko_err_list)})" if isinstance(netmiko_err_list,list) else (netmiko_err_list or "")
  if log.debug_active('netmiko'):
    print(f'Netmiko config errors for {n_data.device}: {netmiko_errors}')
  for cfg_item in n_deploy:
    if node_config.get(cfg_item.replace('.','@'),None) != ':netmiko':
      continue
    cfg_file = f'node_files/{n_data.name}/{cfg_item}'
    if not os.path.exists(cfg_file):
      log.error(f'Skipping {cfg_item} config on {n_data.name}; cannot find {cfg_file}',category=log.FatalError,module='netmiko')
      append_to_list(n_data._deploy,'failed',cfg_item)
      continue
    try:
      if use_script:
        OK = send_script(net_connect,n_data,cfg_item,cfg_file,features)
      else:
        OK = send_config(net_connect,n_data,cfg_item,cfg_file,features,netmiko_errors)
    except Exception as ex:
      OK = False
      log.error(
        f'{cfg_item} configuration failed on {n_data.name}',
        more_data=str(ex),
        more_hints=f'Inspect the session log file {session_log} for more details',
        module='netmiko')

    if not OK:
      append_to_list(n_data._deploy,'failed',cfg_item)
      return

    append_to_list(n_data._deploy,'success',cfg_item)
    n_data._deploy.method = 'Netmiko'

  if log.VERBOSE:
    log.info(f"Configuration session log for {n_data.name} is in {session_log}")
