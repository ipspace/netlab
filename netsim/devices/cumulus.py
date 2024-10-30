#
# Arista EOS quirks
#
from box import Box

from . import _Quirks
from ..utils import log
from ..augment import devices

def check_ospf_vrf_default(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if vdata.get('ospf.default',None):
      log.error(
        f"VRF OSPF default route is not working on Cumulus Linux (node {node.name}, vrf {vname})",
        category=log.IncorrectType,
        module='quirks')

"""
Checks whether any node VLAN is in the (changeable) reserved range
"""
def check_reserved_vlan_range(node: Box) -> None:
  for vname,vdata in node.get('vlans',{}).items():
    vid = vdata.get('id',0)
    if vid>=3725 and vid <=3999:
      log.error(
        f"VLAN id {vid} is in the reserved range 3725-3999 on Cumulus Linux (node {node.name}, vlan {vname})",
        category=log.IncorrectValue,
        module='quirks')

class Cumulus(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'ospf' in mods and 'vrfs' in node:
      check_ospf_vrf_default(node)
    if 'vlan' in mods and 'vlans' in node:
      check_reserved_vlan_range(node)
