#
# Cisco Nexus OS quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


def check_reserved_vlans(node: Box, topology: Box) -> None:
  for vname,vdata in node.get('vlans',{}).items():
    if vdata.id > 3966:
      report_quirk(
        f'Cannot use VLANs above 3966 on Nexus OS (node {node.name}, VLAN {vname}, ID {vdata.id})',
        node=node,
        quirk='vlan.range',
        category=log.IncorrectValue,
        module='quirks')

'''
Nexus OS cannot configure tagged VLAN 1 in a trunk
'''
def vlan_1_tagged(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if 1 in intf.get('vlan.trunk_id',[]) and not intf.get('vlan.access_id',None):
      intf.vlan.access_id = 3967
      intf.vlan.native='fake'
      report_quirk(
        f'Cisco Nexus OS cannot configure tagged VLAN 1 in a trunk.',
        more_data=f'Changing native VLAN to 3967 (node {node.name} {intf.ifname})',
        node=node,
        quirk='vlan.tagged_1',
        category=Warning)

class NXOS(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'vlan' in mods:
      vlan_1_tagged(node,topology)
      check_reserved_vlans(node,topology)
