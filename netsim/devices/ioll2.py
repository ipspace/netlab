#
# Cisco IOSvL2 quirks
#
from box import Box

from . import _Quirks

from .iosvl2 import check_reserved_vlans,vlan_1_tagged
from .iol import IOSXE as _IOSXE

class IOSL2(_IOSXE):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)

    mods = node.get('module',[])
    if 'vlan' in mods:
      vlan_1_tagged(node,topology)
      check_reserved_vlans(node,topology)
