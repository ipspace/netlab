#
# Device quirks -- a framework to deal with devices with 'interesting' implementations
#
# Each device with quirks should have a module file in this directory with a class derived from _Quirks
#
import typing
import os

from box import Box

# Related modules
from ..utils.callback import Callback
from ..utils import log

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

"""
Callback transformation routines

* node_transform: for all nodes, call specified method for every module used by the node
* link_transform: for all links, call specified method for every module used by any node on the link

Note: mod_load is a global cache of loaded modules
"""

mod_load: typing.Dict = {}

def device_quirk(node: Box, topology: Box, method: str = 'device_quirks') -> None:
  global mod_load

  if log.debug_active('quirks'):
    print(f'Processing {method} device quirks')
  device = node.device

  if not device in mod_load:
    dev_quirk = os.path.dirname(__file__)+"/"+device+".py"
    if os.path.exists(dev_quirk):
      mod_load[device] = _Quirks.load(device,topology.defaults.devices.get(device))
    else:
      mod_load[device] = None

  if mod_load[device]:
    mod_load[device].call(method,node,topology)

def process_quirks(topology: Box) -> None:
  for n in topology.nodes.values():
    device_quirk(n,topology)
