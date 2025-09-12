"""
VBMC validation routines
"""

from box import Box
import typing
import re
from netsim.data import global_vars
from netsim import providers

def exec_poweroff_test(id: str, data: Box, topology: Box) -> str:
  ipmi_user: str = data.get('vbmc.ipmi_user', 'admin')
  ipmi_password: str = data.get('vbmc.ipmi_password', 'admin')
  ipmi_port: int = data.get('vbmc.ipmi_port', 6230)
  return f'ipmitool -I lanplus -H {id} -U {ipmi_user} -P {ipmi_password} -p {ipmi_port} power off'

def valid_poweroff_test(id: str, data: Box, topology: Box) -> bool:
  node_name = data.get('name', None)
  _result = global_vars.get_result_dict('_result')
  if 'Chassis Power Control: Down/Off' not in _result.stdout:
      raise Exception(f'Node ({data.name}) did not power down on request.')
  
  p_module = providers.get_provider_module(topology, 'libvirt')
  state = p_module.call('get_lab_status').get(node_name, None)
  if not state.status:
      raise Exception(f'libvirt node state unreadable for ({data.name})')
  elif 'shutoff' not in state.status:
      raise Exception(f'libvirt node state is not \'shutoff\' for ({data.name})')
  return True

