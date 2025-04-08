#
# vJunos-switch quirks
#
from box import Box
from .junos import JUNOS as _JUNOS
from . import report_quirk
from ..utils import log

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

class Junos_switch(_JUNOS):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print(f"*** DEVICE QUIRKS FOR vJunos-switch {node.name}")
    check_evpn_vlan_trunks(node,topology)
    super().device_quirks(node,topology)
