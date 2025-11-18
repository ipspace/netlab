#
# Cisco 8000v (IOS-XR) quirks
#
from box import Box

from . import _Quirks

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

class Cisco8000v(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    vlan_native_subif(node)
