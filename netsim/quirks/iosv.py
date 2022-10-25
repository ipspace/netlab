#
# Arista EOS quirks
#
from box import Box

from . import _Quirks
from .. import common
from ..data import get_from_box
from ..augment import devices

# Cisco IOSv does not support VRRP on BVI interfaces. Go figure...
#
def check_vrrp_bvi(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if get_from_box(intf,'gateway.protocol') != 'vrrp':                 # No VRRP, move on
      continue

    if get_from_box(intf,'type') != 'svi':                              # Not a BVI interface, move on
      continue

    common.error(
      f'Cisco IOSv cannot run VRRP on BVI interfaces.',
      common.IncorrectType,
      'quirks')
    return

class EOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'gateway' in mods:
      check_vrrp_bvi(node,topology)
