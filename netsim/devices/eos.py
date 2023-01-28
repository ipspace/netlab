#
# Arista EOS quirks
#
from box import Box

from . import _Quirks
from .. import common
from ..data import get_from_box
from ..augment import devices

def check_mlps_vlan_bundle(node: Box) -> None:
  if get_from_box(node,'evpn.transport') != 'mpls':                     # This quirk applies only to EVPN/MPLS
    return

  for vname,vdata in node.get('vlans',{}).items():
    if not get_from_box(vdata,'evpn.bundle'):                           # Check only VLANs within a bundle
      continue
    if vdata.get('mode','') != 'bridge':                                # They must be in pure bridging mode
      common.error(
        f'Arista EOS supports only bridge VLANs in an EVPN/MPLS VLAN bundle ({vname} on {node.name})',
        common.IncorrectType,
        'quirks')
    ifname = f'Vlan{vdata.id}'                                          # Now remove the VLAN interface
    node.interfaces = [ intf for intf in node.interfaces if intf.ifname != ifname ]

def check_mpls_clab(node: Box, topology: Box) -> None:
  if devices.get_provider(node,topology) == 'clab':
    common.error(
      f'Arista cEOS ({node.name}) does not support MPLS. Use vEOS VM with libvirt provider',
      common.IncorrectType,
      'quirks')

def check_shared_mac(node: Box, topology: Box) -> None:
  if devices.get_provider(node,topology) != 'clab':
    return

  for intf in node.interfaces:
    if get_from_box(intf,'gateway.protocol') != 'anycast':              # We hope that VRRP works (not tested yet)
      continue

    if get_from_box(intf,'vlan'):                                       # Anycast works on VLAN cEOS interfaces
      continue

    common.error(
      f'Anycast gateway (VARP) on non-VLAN interfaces does not work on Arista cEOS ({node.name}).\n.. Use vEOS VM with libvirt provider',
      common.IncorrectType,
      'quirks')
    return

class EOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'evpn' in mods:
      if common.debug_active('quirks'):
        print(f'Arista EOS: Checking MPLS VLAN bundle for {node.name}')
      check_mlps_vlan_bundle(node)
    if 'mpls' in mods:
      check_mpls_clab(node,topology)
    if 'gateway' in mods:
      check_shared_mac(node,topology)
