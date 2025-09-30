#
# Generic routing module -- static routes
#
import ipaddress
import typing

from box import Box, BoxList

from ...augment import addressing, devices
from ...data import global_vars
from ...utils import log
from ...utils import routing as _rp_utils
from .. import _routing, data
from .normalize import (
  check_routing_object,
)

"""
include_global_static_routes: Include global static routes into node static routes
"""
def include_global_static_routes(o_data: BoxList,o_type: str,node: Box,topology: Box) -> typing.Optional[BoxList]:
  if not isinstance(o_data,list):
    return None

  include_limit = 20
  sr_name = f'Static route list in node {node.name}'

  while True:
    include_rq = False
    for idx in range(len(o_data)):
      sr_data = o_data[idx]
      if 'include' not in sr_data:
        continue

      if sr_data.include not in topology.get('routing.static',{}):
        log.error(
          f'{sr_name} is trying to include non-existent global static route list {sr_data.include}',
          category=log.MissingValue,
          module='routing')
        sr_data.remove = True
        continue

      include_rq = True
      inc_data = topology.routing.static[sr_data.include]
      for sr_entry in inc_data:        
        if 'nexthop' in sr_data:
          sr_entry = sr_entry + { 'nexthop': sr_data.nexthop }
        o_data.append(sr_entry)

      sr_data.remove = True

    if not include_rq:
      return o_data

    o_data = BoxList([ sr_data for sr_data in o_data if not sr_data.get('remove',False) ])
    include_limit -= 1
    if not include_limit:
      log.error(
        f'{sr_name} has exceeded the include depth limit',
        more_hints='You might have a loop of "include" requests',
        category=log.IncorrectValue,
        module='routing')
      return o_data

"""
Get a string identifier for a static route

* Ideally, we'd have IPv4 and/or IPv6 prefixes
* Failing that, we could identify a static route based on its node, prefix, pool or include attributes
* Last resort: maybe we have at least the nexthop info
* Return 'null' if everything else fails :(
"""
def get_static_route_id(sr_data: Box) -> str:
  af_data = [ sr_data[af] for af in log.AF_LIST if af in sr_data ]
  if not af_data:
    af_data = [ f'{kw}: {sr_data[kw]}' for kw in ['node','prefix','pool'] if kw in sr_data ]
  if not af_data and 'nexthop' in sr_data:
    af_data = [ 'nexthop: '+str(sr_data.nexthop)]
  return ','.join(af_data) or 'null'

"""
process_static_routes: Import global static routes into node static routes
"""
def process_static_route_includes(
      o_data: typing.Union[Box,BoxList],
      o_type: str,
      topo_object: Box,
      o_name: str) -> typing.Union[Box,BoxList]:
  if isinstance(o_data,Box):
    for kw in list(o_data.keys()):
      if isinstance(o_data[kw],BoxList):
        o_data[kw] = process_static_route_includes(o_data[kw],o_type,topo_object,o_name)
      else:
        o_data[kw] = process_static_route_includes(BoxList([o_data[kw]]),o_type,topo_object,o_name)
    return o_data
  if not isinstance(o_data,list):
    return o_data

  include_limit = 20
  topology = global_vars.get_topology()
  if topology is None:
    return o_data
  sr_name = 'A global static route list' if topo_object else f'Static route list in node {o_name}'

  while True:
    include_rq = False
    for idx in range(len(o_data)):
      sr_data = o_data[idx]
      if 'include' not in sr_data:
        continue

      if sr_data.include not in topology.get('routing.static',{}):
        log.error(
          f'{sr_name} is trying to include non-existent global static route list {sr_data.include}',
          category=log.MissingValue,
          module='routing')
        sr_data.remove = True
        continue

      include_rq = True
      inc_data = topology.routing.static[sr_data.include]
      for sr_entry in inc_data:        
        if 'nexthop' in sr_data:
          sr_entry = sr_entry + { 'nexthop': sr_data.nexthop }
        o_data.append(sr_entry)

      sr_data.remove = True

    if not include_rq:
      return o_data

    o_data = BoxList([ sr_data for sr_data in o_data if not sr_data.get('remove',False) ])
    include_limit -= 1
    if not include_limit:
      log.error(
        f'{sr_name} has exceeded the include depth limit',
        more_hints='You might have a loop of "include" requests',
        category=log.IncorrectValue,
        module='routing')
      return o_data

"""
Static route import has been done during the normalization phase,
but we still need a fake function for the import/check loop to work
"""
def import_static_routes(idx: int,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  return None

"""
Create next-hop information from neighbor addresses and static route data
"""
def create_nexthop_data(sr_data: Box,ngb_addr: Box, intf: Box) -> Box:
  nh_data = data.get_empty_box()

  for af in log.AF_LIST:
    if af not in ngb_addr:
      continue
    if isinstance(ngb_addr[af],str):
      nh_data[af] = ngb_addr[af]
      nh_data.intf = intf.ifname

  if nh_data and 'vrf' in sr_data.nexthop:
    nh_data.vrf = sr_data.nexthop.vrf

  return nh_data

"""
Extract an address from the NH list into the next-hop information. Further
processing of static routes uses that next-hop information to figure out
whether we have at least one viable next hop for every prefix specified in
the static route
"""
def extract_nh_from_list(nh: Box) -> None:
  for af in log.AF_LIST:
    if af not in nh:
      af_nh = [ nh_entry[af] for nh_entry in nh.nhlist if af in nh_entry ]
      if af_nh:
        nh[af] = af_nh[0]

"""
Extract just the AF information (host or prefix) from a data object

Returns a box with ipv4 and/or ipv6 components, either as prefixes (default)
or host addresses (when keep_prefix = false)
"""
def extract_af_info(addr: Box, keep_prefix: bool = True) -> Box:
  result = data.get_empty_box()
  for af in log.AF_LIST:                      # Iterate over address families
    if af not in addr:                        # AF not present, move on
      continue
    if isinstance(addr[af],bool):
      result[af] = addr[af]
    elif keep_prefix:                         # Do we need a prefix?
      result[af] = _rp_utils.get_prefix(addr[af])
    else:                                     # We need just the host part
      result[af] = _rp_utils.get_intf_address(addr[af])

  return result

"""
When a static route uses a node as a next hop, we have to resolve
that into IPv4/IPv6 addresses. This function returns a list of
next hops (IPv4/IPv6/intf) for directly-connected nodes or control-plane
endpoint information for remote next hops.

Please note that the next-hop list is returned as the 'nhlist' attribute
of the 'nexthop' data structure.
"""
def resolve_node_nexthop(sr_data: Box, node: Box, topology: Box) -> Box:
  nh = data.get_empty_box()
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  node_found = False
  for intf in node.interfaces:
    if intf.get('_phantom_link',False):
      continue
    for ngb in intf.neighbors:
      if ngb.node != sr_data.nexthop.node:
        continue

      node_found = True
      if intf.get('vrf',None) != nh_vrf:
        continue

      ngb_addr = extract_af_info(ngb,keep_prefix=False)
      nh_data = create_nexthop_data(sr_data,ngb_addr,intf)

      if nh_data:
        data.append_to_list(nh,'nhlist',nh_data)
  
  if nh:
    extract_nh_from_list(nh)
  else:
    if node_found:
      log.error(
        f'Next hop {sr_data.nexthop.node} for static route "{get_static_route_id(sr_data)}"'+ \
        f' is connected to node {node.name} but not in VRF {nh_vrf or "default"}',
        category=log.IncorrectValue,
        module='routing')

    nh = extract_af_info(
           _routing.get_remote_cp_endpoint(topology.nodes[sr_data.nexthop.node]),
           keep_prefix=False)

  return nh

"""
Create the gateway-of-last-resort: for all missing address families:

* Iterate over interface neighbors
* Skip neighbors that are not routers
* Skip neighbors that have no usable IP address (LLA/unnumbered does not count)
* Skip neighbors that use DHCP clients

If anything is left, use that as the gateway of last resort
"""
def create_gateway_last_resort(intf: Box, missing_af: Box, topology: Box) -> typing.Tuple[Box,bool]:
  gw_data = data.get_empty_box()
  unnum_ngb = False

  # Get roles that can be default gateways
  gw_roles = global_vars.get_const('gateway.roles',['router','gateway'])

  for af in list(missing_af.keys()):                        # Iterate over all missing AFs
    for ngb in intf.neighbors:                              # Iterate over all interface neighbors
      n_node = topology.nodes[ngb.node]
      if n_node.get('role','router') not in gw_roles:       # Host/bridge neighbors are useless
        continue
      if af not in ngb:                                     # Does the neighbor have an address in desired AF?
        continue
      if ngb[af] is True:                                   # Do we have an unnumbered neighbor?
        unnum_ngb = True                                    # Mark that we found a fishy neighbor
        continue
      if not isinstance(ngb[af],str):                       # Is the neighbor IP address a real address?
        continue
      if ngb.get(f'dhcp.client.{af}',False):                # Is neighbor using a DHCP client?
        continue
      gw_data[af] = ngb[af]                                 # Use neighbor as the gateway of last resort
      missing_af.pop(af,None)                               # One less AF to worry about
      break                                                 # And get out of the neighbor loop

  if gw_data:
    intf.gateway = gw_data                                  # Store the cached data
  return (gw_data,unnum_ngb)                                # ... and return it together with fishy ngb flag

"""
When a static route uses a default gateway as a next hop, we have to resolve
that into IPv4/IPv6 addresses. This function returns a list of default gateway
next hops (IPv4/IPv6/intf).

Please note that the next-hop list is returned as the 'nhlist' attribute of the
'nexthop' data structure.

Finally, this function can be called twice, first trying to get the configured
gateway data (using the "gateway" module), and if that fails with a desperate
call to get the gateway of last resort (create_gw set to True).

The "gateway of last resort" functionality tries to find the first usable
adjacent router (one per AF, potentially on different interfaces) and uses
that as the next hop for the 'gateway' static routes. The collected information
is added to the interface data to speed up the lookup for subsequent static
route entries.
"""
def resolve_gateway_nexthop(sr_data: Box, node: Box, topology: Box, create_gw: bool = False) -> Box:
  nh = data.get_empty_box()
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  found_unnum_ngb = False
  if create_gw:                                         # This is a desperate call for gateway-of-last-resort
    missing_af = data.get_box(node.af)                  # ... so we need to keep the track of missing AFs

  for intf in node.interfaces:
    if intf.get('vrf',None) != nh_vrf:                  # Skip interfaces in wrong VRFs
      continue

    gw_data = intf.get('gateway',{})                    # Do we have the gateway information on the interface?
    if not gw_data:                                     # It might not be present on routers using static routes
      gw_list = [ ngb.gateway for ngb in intf.neighbors if 'gateway' in ngb ]
      if gw_list:                                       # ... so we try to get the information from the neighbors
        gw_data = gw_list[0]                            # ... using the 'gateway' module
        intf.gateway = gw_data                          # ... and cache it for further use

    if not gw_data:                                     # No usable gateway information
      if create_gw:                                     # Are we trying to set up gateway of last resort?
        (gw_data,u_ngb) = create_gateway_last_resort(intf,missing_af,topology)
        found_unnum_ngb = found_unnum_ngb or u_ngb
        if not gw_data:                                 # Found no useful gateway of last resort
          continue                                      # ... move to the next interface

    gw_addr = extract_af_info(gw_data,keep_prefix=False)
    nh_data = create_nexthop_data(sr_data,gw_addr,intf)
    if nh_data:
      data.append_to_list(nh,'nhlist',nh_data)

  if nh:
    extract_nh_from_list(nh)
  else:
    if found_unnum_ngb and '_unnum_warning' not in node:
      log.warning(
        text=f'Host {node.name} is attached only to subnets where all routers have unnumbered interfaces',
        category=log.MissingValue,
        module='routing',
        flag='host_gw',
        hint='host_gw')
      node._unnum_warning = True

  return nh

"""
When a static route uses an IPv4 or IPv6 address as the next hop,
we're trying to find the outgoing interface for directly-connected next hops.

We have to do this for platforms like Linux that do not support indirect next hops.

The next-hop list is returned as the 'nhlist' attribute of the 'nexthop' data structure.
"""
def resolve_nexthop_intf(sr_data: Box, node: Box, topology: Box) -> Box:
  nh = sr_data.nexthop
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  for af in log.AF_LIST:
    if af not in sr_data:
      continue

    nh_addr = ipaddress.ip_interface(nh[af])
    nh_net  = nh_addr.network
    for intf in node.interfaces:                            # Try to find the next-hop interfaces
      if af not in intf or not isinstance(intf[af],str):    # Interface does not have an address in target AF
        continue
      if intf.get('vrf',None) != nh_vrf:                    # Interface is in the wrong VRF
        continue

      # Move on if the next hop does not belong to the interface subnet
      #
      if not nh_net.subnet_of(ipaddress.ip_interface(intf[af]).network):      # type: ignore[arg-type]
        continue

      # Otherwise append the direct next-hop information to the nhlist
      #
      nh_data = data.get_box({ af: nh[af], 'intf': intf.ifname })
      if 'vrf' in sr_data.nexthop:
        nh_data.vrf = sr_data.nexthop.vrf

      data.append_to_list(nh,'nhlist',nh_data)
  
  return nh

"""
Check whether a VRF static route is valid and supported by the device on which it's used
"""
def check_VRF_static_route(sr_data: Box, node: Box, sr_features: Box) -> bool:
  if 'vrf' in sr_data:
    if sr_data.vrf not in node.get('vrfs',{}):
      log.error(
        f'Static route "{get_static_route_id(sr_data)}" in node {node.name}' + \
        f' refers to VRF {sr_data.vrf} which is not defined',
        category=log.IncorrectValue,
        module='routing')
      return False

    if not sr_features.get('vrf',False):
      log.error(
        f'Device {node.device} (node {node.name}) does not support VRF static routes',
        category=log.IncorrectValue,
        module='routing')
      return False
    
  if 'vrf' in sr_data.nexthop:
    if not sr_features.get('inter_vrf',False):
      log.error(
        f'Device {node.device} (node {node.name}) does not support inter-VRF static routes',
        category=log.IncorrectValue,
        module='routing')
      return False
    
    if sr_data.nexthop.vrf and sr_data.nexthop.vrf not in node.get('vrfs',{}):
      log.error(
        f'Next hop of a static route "{get_static_route_id(sr_data)}" in node {node.name}' + \
        f' refers to VRF {sr_data.nexthop.vrf} which is not defined',
        category=log.IncorrectValue,
        module='routing')
      return False
    
  return True

def check_static_routes(idx: int,o_name: str,node: Box,topology: Box) -> None:
  sr_data = node.routing[o_name][idx]
  d_features = devices.get_device_features(node,topology.defaults)
  sr_features = d_features.get('routing.static')
  if not isinstance(sr_features,dict):
    sr_features = data.get_empty_box()

  if 'pool' in sr_data:
    sr_data = sr_data + extract_af_info(topology.addressing[sr_data.pool])
  elif 'prefix' in sr_data:
    sr_data = sr_data + extract_af_info(addressing.evaluate_named_prefix(topology,sr_data.prefix))
  elif 'node' in sr_data:
    sr_data = sr_data + extract_af_info(_routing.get_remote_cp_endpoint(topology.nodes[sr_data.node]))

  if idx == 0:
    check_routing_object(get_static_route_id(sr_data),o_name,node,topology)

  if 'ipv4' not in sr_data and 'ipv6' not in sr_data:
    log.error(
      f'Static route "{get_static_route_id(sr_data)}" in node {node.name} has no usable IPv4 or IPv6 prefix',
      category=log.MissingValue,
      module='routing')
    return

  if 'nexthop' not in sr_data:
    if '_skip_missing' in sr_data:
      sr_data.remove = True
    else:
      log.error(
        f'Static route "{get_static_route_id(sr_data)}" in node {node.name} has no next hop information',
        category=log.MissingValue,
        module='routing')
    return

  if 'vrf' in sr_data or 'vrf' in sr_data.nexthop:
    if not check_VRF_static_route(sr_data,node,sr_features):
      return

  if sr_data.nexthop.get('node',None):
    sr_data.nexthop = resolve_node_nexthop(sr_data,node,topology) + sr_data.nexthop
  elif sr_data.nexthop.get('gateway',None):
    gw_nh = resolve_gateway_nexthop(sr_data,node,topology)
    if not gw_nh:
      gw_nh = resolve_gateway_nexthop(sr_data,node,topology,create_gw=True)
    sr_data.nexthop = gw_nh + sr_data.nexthop
  elif 'ipv4' in sr_data.nexthop or 'ipv6' in sr_data.nexthop:
    resolve_nexthop_intf(sr_data,node,topology)

  for af in ['ipv4','ipv6']:
    if af not in sr_data:
      continue
    
    if af not in sr_data.nexthop:
      if '_skip_missing' in sr_data:
        sr_data.remove = True
      elif 'discard' in sr_data.nexthop:
        if 'discard' in sr_features:
          continue
        log.error(
          f'Device {node.device} (node {node.name}) does not support discard static routes',
          category=log.IncorrectAttr,
          module='routing')        
      else:
        log.error(
          f'A static route for {sr_data[af]} on node {node.name} has no {af} next hop',
          more_data=str(sr_data),
          category=log.MissingValue,
          module='routing')
      return

  if 'nhlist' in sr_data.nexthop:
    sr_data.remove = True
    for af in log.AF_LIST:
      if af not in sr_data:
        continue
      nexthops = [ nh_entry for nh_entry in sr_data.nexthop.nhlist if af in nh_entry ]
      if not nexthops:
        continue
      for (nh_idx,nh_entry) in enumerate(nexthops[:sr_features.get('max_nexthop',256)]):
        sr_entry = data.get_box({ af: sr_data[af], 'nexthop': nh_entry })
        sr_entry.nexthop.idx = nh_idx
        if 'vrf' in sr_data:
          sr_entry['vrf'] = sr_data.vrf

        node.routing[o_name].append(sr_entry)
  else:
    sr_data.nexthop.idx = 0

  node.routing[o_name][idx] = sr_data

def cleanup_static_routes(o_data: BoxList,o_type: str,node: Box,topology: Box) -> None:
  node.routing[o_type] = [ sr_entry for sr_entry in node.routing[o_type] if 'remove' not in sr_entry ]
