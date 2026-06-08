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
def rp_active(data: typing.Any) -> bool:
  return isinstance(data,Box) or bool(data)

def rp_data(node: Box, proto: str, select: list = ['global','vrf']) -> typing.Generator:
  if 'global' in select:
    node_data = node.get(proto,None)
    if rp_active(node_data):
      yield(node_data,[ intf for intf in node.interfaces if proto in intf ],None)

  if 'vrf' in select:
    for vname,vdata in node.get('vrfs',{}).items():
      vrf_data = vdata.get(proto,None)
      if rp_active(vrf_data):
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
  """
  Check whether the specified BGP attribute is supported by the specified node.
  The BGP neighbor data is provided mostly for error messages
  """

  def check_attr_value(value: typing.Any, enabled: Box) -> bool:
    """
    Given an attribute value which could be a list or a string, check whether the value(s)
    are valid for the current device. Note that this is the "supported by the device' check.
    Crazy values should have been filtered by the data validation code.
    """
    if isinstance(value,str):                               # Do we have a string value?
      if not value in enabled.valid:                        # Easy, compare it to the list of supported values
        inv_cache_key = f'_invalid_value.{module}.{attr}'   # Did we already report the error for this value?
        if value in ndata.get(inv_cache_key,[]):
          return False                                      # We did, don't do it twice, just return "failed"
        data.append_to_list(ndata,inv_cache_key,value)      # Remember the value we reported
        log.error(                                          # ... and report unsupported value
          f'Node {ndata.name} (device {ndata.device}) does not support BGP attribute {attr} value {value}',
          log.IncorrectValue,
          module)
        return False
    elif isinstance(value,list):                            # Oh, the value is a list of keywords
      for elem in value:                                    # So we have to iterate over all of them...
        if not check_attr_value(elem,enabled):
          return False

    return True                                             # We cannot check other values, assuming they're OK
  
  enabled = get_device_bgp_feature(attr,ndata,topology)     # Get feature data for the attribute
  if not enabled:                                           # No feature information or not valid?
    log.error(                                              # Report an error
      f'Attribute {attr} used on BGP neighbor {neigh.name} is not supported by node {ndata.name} (device {ndata.device})',
      log.IncorrectValue,
      module)
    return False

  if enabled is True:                                       # Unconditionally supported?
    return True                                             # Cool
  
  if isinstance(enabled,Box):                               # Feature specified as a dict?
    if 'valid' in enabled:                                  # Maybe it contains supported values?
      n_value = neigh.get(attr,True)                        # If so, fetch the attribute value
      return(check_attr_value(n_value,enabled))             # ... and compare it to supported values
    return True

  if not isinstance(enabled,list):                          # The only other option is a list of supported providers
    return True                                             # Not that, must be OK

  n_provider = devices.get_provider(ndata,topology.defaults)
  if n_provider not in enabled:
    if ndata.get(f'_invalid_provider.{attr}',False):        # Did we already report the problem?
      return False
    ndata._invalid_provider[attr] = True
    log.error(                                              # Provider used on node is not supported
      f'Node {ndata.name} (device {ndata.device}) does not support BGP attribute {attr} when running with {n_provider} provider',
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
