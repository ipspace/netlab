#
# Cisco IOSvL2 quirks
#
from box import Box

from ..utils import log
from ..modules import _routing
from ..augment import devices
from . import report_quirk

from .iosv import IOS as _IOS,common_ios_quirks

def check_reserved_vlans(node: Box, topology: Box) -> None:
  for vname,vdata in node.get('vlans',{}).items():
    if vdata.id in range(1002,1006):
      log.error(
        f'Cannot use VLAN ID {vdata.id} (VLAN {vname}) on Cisco IOSvL2 or IOLL2 for historic reasons',
        category=log.IncorrectValue,
        module='quirks')

'''
IOSv (classic) layer-2 image cannot run tagged VLAN 1 in a trunk
'''
def vlan_1_tagged(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if 1 in intf.get('vlan.trunk_id',[]) and not intf.get('vlan.access_id',None):
      intf.vlan.access_id = 1002
      intf.vlan.native='fddi'
      report_quirk(
        f'Cisco IOS layer-2 image cannot configure tagged VLAN 1 in a trunk.',
        more_data=f'Changing native VLAN to 1002 (node {node.name} {intf.ifname})',
        node=node,
        quirk='vlan.tagged_1',
        category=Warning)

class IOSvL2(_IOS):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'vlan' in mods:
      vlan_1_tagged(node,topology)
      check_reserved_vlans(node,topology)

    common_ios_quirks(node,topology)
