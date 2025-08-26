#
# Arista EOS quirks
#
from box import Box

from .. import data
from ..augment import devices
from ..modules import _routing
from ..utils import log
from . import _Quirks, report_quirk


def check_mlps_vlan_bundle(node: Box) -> None:
  if node.get('evpn.transport',None) != 'mpls':                         # This quirk applies only to EVPN/MPLS
    return

  for vname,vdata in node.get('vlans',{}).items():
    if not vdata.get('evpn.bundle',False):                              # Check only VLANs within a bundle
      continue
    if vdata.get('mode','') != 'bridge':                                # They must be in pure bridging mode
      report_quirk(
        text=f'Arista EOS supports only bridge VLANs in an EVPN/MPLS VLAN bundle ({vname} on {node.name})',
        node=node,
        category=log.IncorrectType)
    ifname = f'Vlan{vdata.id}'                                          # Now remove the VLAN interface
    node.interfaces = [ intf for intf in node.interfaces if intf.ifname != ifname ]

def check_mpls_clab(node: Box, topology: Box) -> None:
  if devices.get_provider(node,topology) == 'clab':
    try:
      ceos_version = node.box.split(':')[1]
    except:
      ceos_version = ''

    if ceos_version < '4.32.1F':
      report_quirk(
        text=f'Arista cEOS ({node.name}) versions earlier than 4.32.1F do not support MPLS data plane',
        more_hints = 'To use MPLS with older EOS versions, use vEOS VM with libvirt provider',
        node=node,
        quirk='mpls_data_plane',
        category=Warning)

def check_shared_mac(node: Box, topology: Box) -> None:
  if devices.get_provider(node,topology) != 'clab':
    return

  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'anycast':                  # We hope that VRRP works (not tested yet)
      continue

    if intf.get('vlan',None):                                           # Anycast works on VLAN cEOS interfaces
      continue

    report_quirk(
      text=f'Anycast gateway (VARP) on non-VLAN interfaces does not work on Arista cEOS ({node.name})',
      more_hints="Use vEOS VM with libvirt provider",
      node=node,
      category=log.IncorrectType)
    return

def configure_ceos_attributes(node: Box, topology: Box) -> None:
  serialnumber = node.eos.get('serialnumber',None)
  systemmacaddr = node.eos.get('systemmacaddr',None)
  if not serialnumber and not systemmacaddr:
    return

  if 'clab' not in node or node.clab.kind != "ceos":
    report_quirk(
      f"eos.serialnumber and eos.systemmacaddr can only be set for Arista cEOS containers (node {node.name}).",
      more_hints=['Use libvirt.uuid to influence serial number on EOS virtual machines'],
      node=node,
      category=Warning,
      quirk='serialnumber')
    return
  
  mnt_config = '/mnt/flash/ceos-config'
  for ct in node.get('clab.binds',[]):
    if mnt_config in ct:
      report_quirk(
        text=f"{mnt_config} file is already mapped, unable to configure eos.serialnumber (node {node.name}).",
        node=node,
        category=Warning)
      return

  data.append_to_list(node.clab,'binds',f'clab_files/{node.name}/ceos-config:{mnt_config}')
  data.append_to_list(node.clab,'config_templates',f'ceos-config:{mnt_config}')

def passive_stub_interfaces(node: Box, topology: Box) -> None:
  if devices.get_provider(node,topology) != 'clab':
    return

  for intf in _routing.routing_protocol_interfaces(node,'ospf'):
    if intf.type != 'stub' or 'ipv4' not in intf:
      continue

    report_quirk(
      f'Changed OSPF network type on {node.name}/{intf.ifname} to point-to-point',
      more_hints = [ f'Arista cEOS does not run OSPFv2 on container stub interfaces configured as broadcast networks' ],
      node=node,
      category=Warning,
      quirk='ospf_stub')

    intf.ospf.network_type = 'point-to-point'

def esi_identifier_format(node: Box, topology: Box) -> None:
  # Arista EOS, in EVPN ESI, wants ESI in format: 0000:0000:0000:0000:0000
  for intf in node.interfaces:
    if intf.get('evpn._esi.id'):
      esi = intf.evpn._esi.id.replace(":", "")
      intf.evpn._esi._eos_id = ':'.join(esi[i:i+4] for i in range(0, len(esi), 4))

class EOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'evpn' in mods:
      if log.debug_active('quirks'):
        print(f'Arista EOS: Checking MPLS VLAN bundle for {node.name}')
      check_mlps_vlan_bundle(node)
    if 'mpls' in mods:
      check_mpls_clab(node,topology)
    if 'gateway' in mods:
      check_shared_mac(node,topology)
    if 'ospf' in mods:
      passive_stub_interfaces(node,topology)
    if 'eos' in node:
      configure_ceos_attributes(node,topology)
    if 'evpn.multihoming' in topology.get('plugin',[]):
      esi_identifier_format(node,topology)
