"""
Use netmiko instead of Ansible to deploy device configurations
"""
import inspect
import os
import typing

from box import Box

from ...augment import devices as a_devices
from ...data import append_to_list
from ...utils import log

NETMIKO_IS_MISSING: bool = False
NETMIKO_LOAD_ERROR: str = ''

try:
  import netmiko as _netmiko
except Exception as ex:
  NETMIKO_LOAD_ERROR = str(ex)
  NETMIKO_IS_MISSING = True

def check_netmiko(n_data: Box) -> bool:
  """
  Check is we have working netmiko module, generate error on first reference
  """
  global NETMIKO_IS_MISSING, NETMIKO_LOAD_ERROR

  if not NETMIKO_IS_MISSING:                      # Did we manage to load netmiko?
    return True                                   # ... cool, life is good

  if NETMIKO_LOAD_ERROR:                          # Did we already scream at the user?
    log.error(f'Cannot load netmiko library to configure {n_data.name}: {NETMIKO_LOAD_ERROR}',category=log.FatalError,module='netmiko')
    NETMIKO_LOAD_ERROR = ''

  return False

NETMIKO_GROUP_VARS: dict = {
  'netmiko_device_type': 'device_type',
  'ansible_user': 'username',
  'ansible_ssh_pass': 'password',
  'ansible_become_password': '*secret'
}

def prepare_params(n_data: Box, topology: Box) -> typing.Optional[dict]:
  """
  Prepare netmiko connection parameters
  """
  global NETMIKO_GROUP_VARS

  config_err_list = []                            # Accumulated list of errors
  netmiko_params:dict = {}                        # Netmiko connection parameters

  for gv,np in NETMIKO_GROUP_VARS.items():        # Translate netsim parameters into netmiko parameters
    gv_value = a_devices.get_node_group_var(n_data,gv,topology.defaults)
    if gv_value is not None:                      # We got a value, but be careful: the target could be optional (marked with '*')
      netmiko_params[np.replace('*','')] = gv_value
    elif '*' not in np:                           # Are we missing a value for a non-optional target?
      config_err_list.append(f'{gv} node/group variable is not set')

  netmiko_host = n_data.mgmt.get('ipv4',None) or n_data.mgmt.get('ipv6',None)
  if not netmiko_host:                            # Finally, try to add management IP address
    config_err_list.append('Cannot use netmiko with devices that have no management IP addresses')
  else:
    netmiko_params['host'] = netmiko_host

  if config_err_list:                             # Any errors so far?
    log.error(
      f'Cannot use netmiko to configure {n_data.name} (device {n_data.device})',
      more_hints=config_err_list,
      category=log.MissingValue,
      module='netmiko')
    return None

  # Cool, we're good to go. Just the final detail: add session log file
  #
  netmiko_params['session_log'] = f'node_files/{n_data.name}/netmiko.log'
  return netmiko_params

def connect(n_data: Box, netmiko_params: dict) -> typing.Optional[_netmiko.BaseConnection]:
  """
  Use netmiko to open a SSH session to a lab device
  """
  try:
    net_connect = _netmiko.ConnectHandler(**netmiko_params)
    if log.VERBOSE:
      log.info(f'Connected to {n_data.name}',module='netmiko')
  except Exception as ex:
    log.error(
      f'netmiko cannot connect to {n_data.name}',
      more_data=[ str(ex) ],
      category=log.FatalError,
      module='netmiko')
    return None

  return net_connect

def deploy(n_data: Box,topology: Box,n_deploy: list) -> None:
  node_config = n_data.get('_node_config',None)
  if not node_config:
    return

  if not check_netmiko(n_data):
    return

  netmiko_params = prepare_params(n_data,topology)
  if not netmiko_params:
    return None

  net_connect = connect(n_data,netmiko_params)
  if not net_connect:
    return

  session_log = netmiko_params["session_log"]
  netmiko_err_list = a_devices.get_node_group_var(n_data,'netmiko_error_regexp',topology.defaults)
  netmiko_errors = rf"({'|'.join(netmiko_err_list)})" if isinstance(netmiko_err_list,list) else (netmiko_err_list or "")
  for cfg_item in n_deploy:
    if node_config.get(cfg_item.replace('.','@'),None) != ':netmiko':
      return
    cfg_file = f'node_files/{n_data.name}/{cfg_item}'
    if not os.path.exists(cfg_file):
      log.error(f'Skipping {cfg_item} config on {n_data.name}; cannot find {cfg_file}',category=log.FatalError,module='netmiko')
      continue
    try:
      net_connect.send_config_from_file(cfg_file,error_pattern=netmiko_errors)
      log.info(f'Sent {cfg_item} configuration to {n_data.name}',module='netmiko')
      if inspect.getattr_static(net_connect,'commit') is not _netmiko.BaseConnection.commit:
        net_connect.commit()
      if cfg_item in ['normalize','initial']:
        net_connect.set_base_prompt()
      append_to_list(n_data._deploy,'success',cfg_item)
    except Exception as ex:
      append_to_list(n_data._deploy,'failed',cfg_item)
      log.error(
        f'{cfg_item} configuration failed on {n_data.name}',
        more_data=str(ex),
        more_hints=f'Inspect the session log file {session_log} for more details',
        module='netmiko')
      return

  if log.VERBOSE:
    log.info(f"Configuration session log for {n_data.name} is in {session_log}")
