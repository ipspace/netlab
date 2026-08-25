"""
netmiko utility functions

* Check whether we can use netmiko
* Prepare netmiko connection parameters from node/topology data
* Connect to a device via SSH
"""
import inspect
import typing

from box import Box

from ..augment import devices as a_devices
from . import log

NETMIKO_IS_MISSING: bool = False
NETMIKO_LOAD_ERROR: str = ''

try:
  import netmiko as _netmiko  # type: ignore # Do not try to type-check netmiko if it's missing
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
    log.error(
      f'Cannot load netmiko library to configure {n_data.name}: {NETMIKO_LOAD_ERROR}',
      more_hints='use "pip3 install netmiko" or equivalent to install it',
      category=log.FatalError,
      module='netmiko')
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

def connect(n_data: Box, netmiko_params: dict) -> 'typing.Optional[_netmiko.BaseConnection]':
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

def has_commit(conn: '_netmiko.BaseConnection') -> bool:
  """
  Does the netmiko connection support commit() call?
  """
  if NETMIKO_IS_MISSING:
    return False

  return inspect.getattr_static(conn,'commit') is not _netmiko.BaseConnection.commit
