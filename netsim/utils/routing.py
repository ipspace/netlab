#
# BGP neighbor traversal utilities
#

import ipaddress
import typing

from box import Box

from .. import data
from ..augment import devices
from . import log


# Return IP address from int, address, or prefix
#
def get_ipv4_address(addr: typing.Union[str,int]) -> str:
  return str(ipaddress.IPv4Interface(addr).ip)

def get_intf_address(addr: typing.Union[str,int]) -> str:
  return str(ipaddress.ip_interface(addr).ip)

def get_address(addr: str) -> str:
  return str(ipaddress.ip_address(addr))

def get_prefix(addr: str) -> str:
  return str(ipaddress.ip_interface(addr).network)

# try_intf_address is used when validation functions need an IP address from an
# interface address. The target address could be hostname, so we only try our best
#
def try_intf_address(addr: str) -> str:
  try:
    return get_intf_address(addr)
  except:
    return addr

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
Mark a BGP session that needs to be cleared in the configuration template
'''
def clear_bgp_session(node: Box, ngb: Box) -> None:
  for af in log.AF_LIST:                              # Check all relevant address families
    if af not in ngb:                                 # ... neighbor not using this AF, move on
      continue

    # Otherwise, add the neighbor address to the global- or VRF bgp._session_clear list
    #
    bgp_data = node.bgp if '_src_vrf' not in ngb else node.vrfs[ngb._src_vrf].bgp
    data.append_to_list(bgp_data,'_session_clear',ngb[af])

'''
rp_data: iterate over routing protocol instances (global and VRF)
'''
def rp_data(node: Box, proto: str, select: list = ['global','vrf']) -> typing.Generator:
  if 'global' in select:
    if proto in node:
      yield(node[proto],[ intf for intf in node.interfaces if proto in intf ],None)

  if 'vrf' in select:
    for vname,vdata in node.get('vrfs',{}).items():
      if proto in vdata:
        yield(vdata[proto],vdata[proto].get('interfaces',[]),vname)

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
