#
# BGP neighbor traversal utilities
#

from box import Box
import typing

# Return all global and optionaly VRF neighbors
#
def neighbors(node: Box, vrf: bool = True) -> typing.Generator:
  for ngb in node.get('bgp.neighbors',[]):
    yield ngb

  if not vrf:
    return

  for vdata in node.get('vrfs',{}).values():
    for ngb in vdata.get('bgp.neighbors',[]):
      yield ngb

# Return all BGP neighbors associated with interfaces (usually EBGP neighbors)
#
def intf_neighbors(node: Box, vrf: bool = True) -> typing.Generator:
  for intf in node.interfaces:
    if 'vrf' in intf:
      if not vrf:
        continue
      for ngb in node.vrfs[intf.vrf].get('bgp.neighbors',[]):
        if ngb.get('ifindex',None) == intf.ifindex:
          yield (intf,ngb)
    else:
      for ngb in node.get('bgp.neighbors',[]):
        if ngb.get('ifindex',None) == intf.ifindex:
          yield (intf,ngb)
