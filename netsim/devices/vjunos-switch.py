#
# vJunos-switch quirks
#
from box import Box

from ..modules import vrf
from ..utils import log
from . import report_quirk
from .junos import JUNOS as _JUNOS


def check_evpn_vlan_trunks(node: Box, topology: Box) -> None:
  if 'evpn' not in node.get('module',[]):
    return
  
  e_vlan = node.get('evpn.vlans',[])
  if not e_vlan:
    return
  
  if node.get('evpn._junos_default_macvrf',False) is not False:
    return
  
  for intf in node.interfaces:
    v_trunk = intf.get('vlan.trunk',{})
    if not v_trunk:
      continue
    for vname in v_trunk:
      if vname in e_vlan:
        report_quirk(
          f'node {node.name} cannot use EVPN-enabled VLAN {vname} on a VLAN trunk on interface {intf.ifname}',
          node=node,
          category=log.IncorrectType,
          more_hints=['The node is using VLAN-based EVPN service which cannot be used with enterprise-style VLAN trunks'],
          quirk='evpn_macvrf')

def macvrf_unique_rd_for_vlan_bundle(node: Box, topology: Box) -> None:
  if 'evpn' not in node.get('module',[]):
    return
  if 'vrf' not in node.get('module',[]):
    return
  asn = vrf.get_rd_as_number(node, topology)
  if asn is None:
    return

  for vname,vdata in node.vrfs.items():
    if vdata.get('evpn.bundle'):
      # in that case we need to generate a new RD for the mac-vrf (cannot be the same of L3 VRF)
      free_vrf_idx = vrf.get_next_vrf_id(asn)
      vdata._junos_l2vrf_rd = free_vrf_idx[1]

class Junos_switch(_JUNOS):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print(f"*** DEVICE QUIRKS FOR vJunos-switch {node.name}")
    check_evpn_vlan_trunks(node,topology)
    macvrf_unique_rd_for_vlan_bundle(node,topology)
    super().device_quirks(node,topology)
