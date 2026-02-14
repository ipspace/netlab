#
# Cisco IOS-XE quirks
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Quirks, report_quirk
from .iosv import check_ripng_passive


def check_srv6_sid(node: Box, topology: Box) -> None:
  if node.get('srv6.allocate_loopback',False):
    report_quirk(
      f'SRv6 SID on Cisco IOS-XE cannot overlap with the loopback address',
      node,
      quirk='srv6.sid',
      more_hints=['Set the srv6.allocate_loopback parameter to False'],
      category=log.IncorrectValue)

def check_vni(node: Box, topology: Box) -> None:
  if 'vxlan' not in node.get('module',[]):
    return
  for vname,vdata in node.get('vlans',{}).items():
    vni = vdata.get('vni',None)
    if not vni:
      continue
    if vni < 4096:
      report_quirk(
        f'Cisco IOS-XE cannot use VNI values below 4096 (VLAN {vname} on node {node.name})',
        node,
        quirk='vxlan.vni',
        category=log.IncorrectValue)

def evpn_transit_vlan(node: Box, topology: Box) -> None:
  if 'evpn' not in node.get('module',[]):
    return
  
  vlan_set = { vdata.id for vdata in node.get('vlans',{}).values() }
  xvlan_id = devices.get_node_group_var(node,'netlab_evpn_transit_vlan',topology.defaults) or 3700

  for vdata in node.get('vrfs',{}).values():
    if 'evpn.transit_vni' not in vdata:
      continue
    while xvlan_id in vlan_set:
      xvlan_id += 1
    vdata.evpn._transit_vlan = xvlan_id

class IOSXE(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_ripng_passive(node,topology)
    check_srv6_sid(node,topology)
    check_vni(node,topology)
    evpn_transit_vlan(node,topology)
