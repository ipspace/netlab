#
# Device quirks -- a framework to deal with devices with 'interesting' implementations
#
# Each device with quirks should have a module file in this directory with a class derived from _Quirks
#
import json
import os
import typing

from box import Box

from ..data.global_vars import get_topology
from ..utils import log

# Related modules
from ..utils.callback import Callback


class _Quirks(Callback):

  def __init__(self, data: Box) -> None:
    pass

  @classmethod
  def load(self, device: str, data: Box) -> typing.Any:
    module_name = __name__+"."+device
    obj = self.find_class(module_name)
    if obj:
      return obj(data)
    else:
      log.fatal(f'Cannot load {device} quirks, aborting')
      return None

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    log.fatal(f'{node.device} quirks module does not implement device_quirks method')

  def check_config_sw(self, node: Box, topology: Box) -> None:
    pass

"""
Get the quirks module for the specified device

Note: DEVICE_MODULE is a global cache of loaded modules
"""

DEVICE_MODULE: typing.Dict = {}

def get_device_module(device: str, topology: Box) -> typing.Optional[typing.Any]:
  global DEVICE_MODULE

  if device in DEVICE_MODULE:
    return DEVICE_MODULE[device]

  dev_quirk = os.path.dirname(__file__)+"/"+device+".py"
  if os.path.exists(dev_quirk):
    DEVICE_MODULE[device] = _Quirks.load(device,topology.defaults.devices.get(device))
  else:
    DEVICE_MODULE[device] = None

  return DEVICE_MODULE[device]

"""
Execute a device quirk callback
"""
def exec_device_quirk(node: Box, topology: Box, method: str = 'device_quirks') -> None:

  if log.debug_active('quirks'):
    print(f'Processing device quirks: method {method}, node {node.name}/{node.device}')

  q_module = get_device_module(node.device,topology)
  if q_module is not None:
    q_module.call(method,node,topology)

"""
Process device quirks at the end of the topology transformation
"""
def process_quirks(topology: Box) -> None:
  for n in topology.nodes.values():
    exec_device_quirk(n,topology)

ANSIBLE_COLLECTIONS: dict = {}

def get_ansible_collection(cname: str) -> typing.Optional[dict]:
  global ANSIBLE_COLLECTIONS
  from ..cli import external_commands

  if ANSIBLE_COLLECTIONS:
    return ANSIBLE_COLLECTIONS.get(cname,None)

  result = external_commands.run_command(
            cmd='ansible-galaxy collection list --format json',
            check_result=True,return_stdout=True,run_always=True)
  if not isinstance(result,str):
    ANSIBLE_COLLECTIONS['_failed'] = True
    log.error('Cannot run ansible-galaxy to get the list of installed collections',log.MissingDependency)
    return None

  try:
    ac_list = json.loads(result)              # ansible-galaxy returns a dictionary of dicts
    for loc_v in ac_list.values():            # Iterate over returned locations
      for ack,acv in loc_v.items():           # Iterate over collections
        if ack not in ANSIBLE_COLLECTIONS:    # ... and keep the first one found
          ANSIBLE_COLLECTIONS[ack] = acv

  except Exception:
    log.fatal('Cannot parse the ansible-galaxy JSON printout: {ex}')

  return ANSIBLE_COLLECTIONS.get(cname,None)

COLLECTION_WARNING: dict = {}

def need_ansible_collection(
      node: Box,
      cname: str,
      version: typing.Optional[str] = None,
      install: str = '') -> bool:
  global COLLECTION_WARNING

  cdata = get_ansible_collection(cname)
  if cdata is not None:
    if version is None:
      return True
    if cdata.get('version','0') >= version:
      return True
  
  if node.device in COLLECTION_WARNING:
    return False
  
  if not install:
    install = f'ansible-galaxy collection install {cname}'
  v_txt = f' (version {version})' if version else ''

  log.error(
        f'We need Ansible collection {cname}{v_txt} to configure {node.device} devices',
        category=log.MissingDependency,
        more_hints = [ f'Use "{install}" to install it' ],
        module='devices')
  COLLECTION_WARNING[node.device] = True
  return False

def process_config_sw_check(topology: Box) -> None:
  for n in topology.nodes.values():
    exec_device_quirk(n,topology,method='check_config_sw')

  log.exit_on_error()

def report_quirk(text: str, node: Box, quirk: str = '', **kwargs: typing.Any) -> None:
  topology = get_topology()

  # Check the defaults to see if we have to report the quirk
  #
  q_path = f'defaults.devices.{node.device}.warnings.{quirk}'
  if topology is not None and quirk:
    q_state = topology.get(q_path,True)
    if not q_state:
      return
  
  # Set category and module if they're not specified
  #
  if 'category' not in kwargs:
    kwargs['category'] = log.IncorrectValue
  if 'module' not in kwargs:
    kwargs['module'] = node.device

  # Add the 'this is how you disable this quirk' hint
  #
  if quirk:
    q_disable = 'hide this warning' if kwargs['category'] is Warning else 'disable this check'
    q_hint = f'Set {q_path} to False to {q_disable}'
    if 'more_hints' in kwargs and isinstance(kwargs['more_hints'],list):
      kwargs['more_hints'].append(q_hint)
    else:
      kwargs['more_hints'] = [ q_hint ]

  # Now hope for the best ;)
  log.error(text,**kwargs)
