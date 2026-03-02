#
# Cisco 8000v (IOS-XR) quirks
#
import typing

from box import Box

from ..data import global_vars
from ..utils import log
from . import _Quirks, report_quirk

"""
IOS XR needs native L2 subinterfaces to make native bridged VLANs work.

This function identifies interfaces that are really native VLANs in disguise
and sets the _xr_native_subif string to create a complete interface name in
the configuration templates
"""
def vlan_native_subif(node: Box) -> None:
  if 'vlan' not in node.get('module',[]):
    return
  for intf in node.interfaces:
    access_vlan = intf.get('vlan.access_id',None)     # No access_id on LAN interface, no native VLAN
    if not access_vlan:
      continue
    intf._xr_native_subif = ''                        # Assume we don't need an extra subinterface
    if intf.type != 'lan':                            # Not a LAN interface, not interesting
      continue
    trunk_vlans = intf.get('vlan.trunk_id',[])        # if the access VLAN is not in the trunk VLAN list
    if access_vlan not in trunk_vlans:                # ... this is not a trunk interface with native VLAN
      continue
    intf._xr_native_subif = f'.{access_vlan}'         # oops, there goes the native subif

ANYCAST_ATTR: dict = {
  'gateway.ipv4': 'ipv4',
  'gateway.ipv6': 'ipv6',
  'gateway.anycast.mac': 'mac_address'
}

RP_LIST: typing.Optional[Box] = None

def evpn_anycast(node: Box, topology: Box) -> None:
  global ANYCAST_ATTR, RP_LIST

  node_mods = node.get('module',[])
  if 'gateway' not in node_mods:                          # No gateway module, nothing to worry
    return
  anycast_list = []
  for intf in node.interfaces:
    if intf.get('gateway.protocol','') != 'anycast':
      continue

    intf_desc = f'{intf.ifname} ({intf.name})'
    if intf.type != 'svi':
      anycast_list.append(intf_desc)
      continue
    vdata = node.get(f'vlans.{intf.vlan.name}',{})
    if 'evpn' not in vdata:
      anycast_list.append(intf_desc)
      continue

    if not RP_LIST:
      RP_LIST = global_vars.get_const('routing_protocols',[])
    kw_list = [ kw for kw in intf.keys() if kw in RP_LIST ]
    if kw_list:
      report_quirk(
        f'{",".join(kw_list)} cannot be used on an interface with anycast gateway',
        node=node,
        quirk='anycast_rp',
        more_data=[f'Node {node.name} interface {intf_desc}'],
        category=log.IncorrectAttr)

    for gw_attr,intf_attr in ANYCAST_ATTR.items():      # Copy gateway/anycast attributes to corresponding
      if gw_attr in intf:                               # ... interface attributes. Unfortunately, that's the kludge
        intf[intf_attr] = intf[gw_attr]                 # ... Cisco uses to implement anycast GW

  if anycast_list:
    report_quirk(
      f'{node.name}: Anycast gateway can be used only on SVI/VLAN interfaces in EVPN MAC-VRFs',
      node=node,
      quirk='anycast_evpn',
      more_data=[f'Interface(s): {",".join(anycast_list)}'],
      category=log.IncorrectType)

class Cisco8000v(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    vlan_native_subif(node)
    evpn_anycast(node,topology)