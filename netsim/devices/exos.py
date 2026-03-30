from box import Box

from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk

EXOS_DEFAULT_VLAN_NAME = 'Default'


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


def rename_vlan_references(intf: Box, old_name: str, new_name: str) -> None:
  if intf.get('vlan.access',None) == old_name:
    intf.vlan.access = new_name
  if intf.get('vlan.native',None) == old_name:
    intf.vlan.native = new_name
  if intf.get('vlan.name',None) == old_name:
    intf.vlan.name = new_name
  if intf.get('vlan_name',None) == old_name:
    intf.vlan_name = new_name
  if intf.get('_vlan_native',None) == old_name:
    intf._vlan_native = new_name

  trunk = intf.get('vlan.trunk',None)
  if trunk and old_name in trunk:
    trunk[new_name] = trunk.pop(old_name)


def rename_vlan_1_to_default(node: Box) -> None:
  if 'vlans' not in node:
    return

  vlan_1_name = next(
    (vname for vname,vdata in node.vlans.items() if vdata.get('id',None) == 1 and vname != EXOS_DEFAULT_VLAN_NAME),
    None)
  if not vlan_1_name:
    return

  if EXOS_DEFAULT_VLAN_NAME in node.vlans:
    node.vlans[EXOS_DEFAULT_VLAN_NAME] = node.vlans[EXOS_DEFAULT_VLAN_NAME] + node.vlans[vlan_1_name]
    node.vlans.pop(vlan_1_name,None)
  else:
    node.vlans[EXOS_DEFAULT_VLAN_NAME] = node.vlans.pop(vlan_1_name)

  for intf in node.interfaces:
    rename_vlan_references(intf,vlan_1_name,EXOS_DEFAULT_VLAN_NAME)

  report_quirk(
    text='Extreme EXOS reserves VLAN ID 1 for the built-in Default VLAN',
    more_data=f'Renaming VLAN {vlan_1_name} to {EXOS_DEFAULT_VLAN_NAME} on node {node.name}',
    node=node,
    quirk='vlan.default_1',
    category=Warning)


class EXOS(_Quirks):

  @classmethod
  def device_quirks(cls, node: Box, topology: Box) -> None:
    if 'vlan' in node.get('module',[]):
      rename_vlan_1_to_default(node)
    if 'gateway' in node.get('module',[]):
      check_vrrp_address_families(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'community.network',version='5.1.0')
