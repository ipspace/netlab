from box import Box

from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk

EXOS_VLAN_1_NAME = 'Default'

def check_vrrp_address_families(node: Box) -> None:
  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'vrrp':
      continue

    if 'ipv4' in intf.gateway and 'ipv6' in intf.gateway:
      report_quirk(
        text=f'Extreme EXOS cannot configure IPv4 and IPv6 virtual addresses in the same VRRP instance ({node.name} {intf.ifname})',
        node=node,
        quirk='vrrp_mixed_af',
        category=log.IncorrectType)
      return

def rename_interface_vlan_references(intf: Box, old_name: str, new_name: str) -> None:
  for kw in ('vlan.access','vlan.native','vlan.name','vlan_name','_vlan_native'):
    if intf.get(kw,None) == old_name:
      intf[kw] = new_name

  trunk = intf.get('vlan.trunk',None)
  if trunk and old_name in trunk:
    trunk[new_name] = trunk.pop(old_name)

def default_vlan_1(node: Box) -> None:
  if 'vlans' not in node:
    return

  if EXOS_VLAN_1_NAME in node.vlans and node.vlans[EXOS_VLAN_1_NAME].id != 1:
    report_quirk(
      text=f'{EXOS_VLAN_1_NAME} VLAN must have VLAN tag 1',
      node=node,
      category=log.IncorrectValue)
    return

  vlan_1_name = next(
    (vname for vname,vdata in node.vlans.items() 
       if vdata.get('id',None) == 1 and vname != EXOS_VLAN_1_NAME),
    None)
  if not vlan_1_name:
    return

  node.vlans[EXOS_VLAN_1_NAME] = node.vlans.pop(vlan_1_name)

  for intf in node.interfaces:
    rename_interface_vlan_references(intf,vlan_1_name,EXOS_VLAN_1_NAME)

  report_quirk(
    text='Extreme EXOS reserves VLAN ID 1 for the built-in Default VLAN',
    more_data=f'Renaming VLAN {vlan_1_name} to {EXOS_VLAN_1_NAME} on node {node.name}',
    node=node,
    quirk='vlan.default_1',
    category=Warning)

class EXOS(_Quirks):

  @classmethod
  def device_quirks(cls, node: Box, topology: Box) -> None:
    if 'vlan' in node.get('module',[]):
      default_vlan_1(node)
    if 'gateway' in node.get('module',[]):
      check_vrrp_address_families(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'community.network',version='5.1.0')
