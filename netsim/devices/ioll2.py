#
# Cisco IOSvL2 quirks
#
from box import Box

from ..utils import log
from ..utils import routing as _routing
from . import report_quirk
from .iol import IOSXE as _IOSXE
from .iosvl2 import check_reserved_vlans, lag_remove_virtual, vlan_1_tagged


def check_ospfv3_bfd(node: Box) -> None:
  for rp_data,_,_ in _routing.rp_data(node,'ospf'):
    if rp_data.get('bfd',False) and rp_data.get('af.ipv6',False):
      report_quirk(
        f'Cisco IOL L2 image cannot configure BFD for OSPFv3 (node {node.name})',
        node=node,
        quirk='ospfv3_bfd',
        category=log.IncorrectAttr)
      return

class IOSL2(_IOSXE):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)

    mods = node.get('module',[])
    if 'vlan' in mods:
      vlan_1_tagged(node,topology)
      check_reserved_vlans(node,topology)
    if 'ospf' in mods and 'bfd' in mods:
      check_ospfv3_bfd(node)
    if 'lag' in mods:
      lag_remove_virtual(node,topology)  
