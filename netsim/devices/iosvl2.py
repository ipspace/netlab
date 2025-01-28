#
# Cisco IOSvL2 quirks
#
from box import Box

from ..utils import log
from ..modules import _routing
from ..augment import devices

from .iosv import IOS as _IOS,common_ios_quirks

def check_reserved_vlans(node: Box, topology: Box) -> None:
  for vname,vdata in node.get('vlans',{}).items():
    if vdata.id in range(1002,1006):
      log.error(
        f'Cannot use VLAN ID {vdata.id} (VLAN {vname}) on Cisco IOSvL2 or IOLL2 for historic reasons',
        category=log.IncorrectValue,
        module='quirks')

class IOSvL2(_IOS):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    common_ios_quirks(node,topology)
    check_reserved_vlans(node,topology)
