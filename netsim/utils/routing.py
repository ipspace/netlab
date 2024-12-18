#
# BGP neighbor traversal utilities
#

from box import Box
from . import log
from ..augment import devices
import typing

# Return all global and optionaly VRF neighbors
#
def neighbors(node: Box, vrf: bool = True, select: list = ['ibgp','ebgp']) -> typing.Generator:
  if 'bgp' not in node:
    return

  for ngb in node.get('bgp.neighbors',[]):
    if ngb.type in select:
      yield ngb

  if not vrf:
    return

  for vname,vdata in node.get('vrfs',{}).items():
    for ngb in vdata.get('bgp.neighbors',[]):
      if ngb.type in select:
        ngb._src_vrf = vname
        yield ngb

# Return all BGP neighbors associated with interfaces (usually EBGP neighbors)
#
def intf_neighbors(node: Box, vrf: bool = True, select: list = ['ibgp','ebgp']) -> typing.Generator:
  for intf in node.interfaces:
    if 'vrf' in intf:
      if not vrf:
        continue
      for ngb in node.vrfs[intf.vrf].get('bgp.neighbors',[]):
        if ngb.get('ifindex',None) == intf.ifindex and ngb.type in select:
          yield (intf,ngb)
    else:
      for ngb in node.get('bgp.neighbors',[]):
        if ngb.get('ifindex',None) == intf.ifindex and ngb.type in select:
          yield (intf,ngb)

'''
igp_interfaces: iterate over IGP interfaces (global and VRF)
'''
def igp_interfaces(node: Box, proto: str, vrf: bool = True) -> typing.Generator:
  for intf in node.interfaces:
    if proto not in intf:
      continue
    yield(intf)

  if not vrf:
    return
  
  for vname,vdata in node.get('vrfs',{}).items():
    if proto not in vdata or 'interfaces' not in vdata[proto]:
      continue
    for intf in vdata[proto].interfaces:
      if not 'proto' in intf:
        continue
      yield(intf)

'''
check_device_attribute_support -- using device BGP features, check whether the
device supports the attribute applied to a BGP neighbor
'''
def get_device_bgp_feature(attr: str, ndata: Box, topology: Box) -> typing.Optional[typing.Any]:
  features = devices.get_device_features(ndata,topology.defaults)
  return features.bgp.get(attr,None)

def check_device_attribute_support(attr: str, ndata: Box, neigh: Box, topology: Box, module: str) -> bool:
  enabled = get_device_bgp_feature(attr,ndata,topology)
  if not enabled:
    log.error(
      f'Attribute {attr} used on BGP neighbor {neigh.name} is not supported by node {ndata.name} (device {ndata.device})',
      log.IncorrectValue,
      module)
    return False

  if not isinstance(enabled,list):
    return True

  if not topology.provider in enabled:
    log.error(
      f'Node {ndata.name} (device {ndata.device}) does not support BGP attribute {attr} when running with {topology.provider} provider',
      log.IncorrectValue,
      module)
    return False

  return True

'''
Remove session attributes with local significance from BGP neighbors
because they are neighbors' attributes, not ours
'''
def cleanup_neighbor_attributes(ndata: Box, topology: Box, clist: list) -> None:
  for ngb in neighbors(ndata):
    for attr in clist:
      ngb.pop(attr,None)
