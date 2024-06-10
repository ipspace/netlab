
"""
Routing Protocol utility functions:

* network_type: set IGP network type on a link. Used by OSPF and IS-IS
* routing_af: set routing protocol address families for a node
* external: return True is an interface is an external interface, and removes IGP-related parameters from the interface
* passive: set IGP 'passive' flag on an interface
"""

from box import Box
import typing
import netaddr

from ..utils import log
from ..augment import addressing,devices
from .. import data

# Build routing protocol address families
#
# * If the address families are not set, calculate them based on interface address families
# * Otherwise parse and validate the AF attribute
#
def routing_af(node: Box, proto: str, features: typing.Optional[Box] = None) -> None:
  if 'af' in node[proto]:               # Is the AF attribute set for the routing protocol?
    if isinstance(node[proto].af,list): # Turn a list of address families into a dictionary
      node[proto].af = { af: True for af in node[proto].af }

    if node[proto].af is None:
      node[proto].pop('af',None)
    else:
      if not isinstance(node[proto].af,dict):
        log.error(
          f'af attribute for {proto} on node {node.name} has to be a list or a dictionary',
          log.IncorrectValue,
          proto)
        return

      for proto_af in node[proto].af.keys():
        if not proto_af in ('ipv4','ipv6'):
          log.error(
            f'Routing protocol address family has to be ipv4 and/or ipv6: {proto} on {node.name}',
            log.IncorrectValue,
            proto)

  if not 'af' in node[proto]:                         # No configured AF attribute, calculate it
    for af in ['ipv4','ipv6']:
      if af in node.get('loopback',{}):               # Address family enabled on loopback?
        node[proto].af[af] = True                     # ... we need it in the routing protocol
        continue

      for l in node.get('interfaces',[]):             # Scan all interfaces
        if af in l and proto in l and not 'vrf' in l: # Do we have AF enabled on any global interface?
          node[proto].af[af] = True                   # Found it - we need it the module
          continue

  p_features = features.get(proto,{}) if features else {}

  for af in ['ipv4','ipv6']:                          # Remove unused address families
    if not node[proto].af.get(af,False):
      node[proto].af.pop(af,False)
      continue

    if af in p_features and p_features[af] is False:
      log.error(
        f'Device {node.device} (node {node.name}) cannot run {proto} on {af}',
        log.IncorrectValue,
        proto)

# Set network type for an interface:
#
# * If the network type is specified, validate it against a list of allowed network types
# * Otherwise, set network type to P2P if the interface has two nodes attached to it
#
def network_type(
      intf: Box,
      proto: str,
      allowed: typing.List[str] = ['point-to-point'],
      p2p: str = 'point-to-point') -> typing.Optional[str]:
  if 'network_type' in intf[proto]:                 # Did the user specify network type?
    if not intf[proto].network_type:                # ... she did and she wants it gone
      intf[proto].pop('network_type')
    else:
      if intf[proto].network_type not in allowed:   # ... did she specify a valid value?
        return(f"Invalid {proto} network type {intf[proto].network_type}")
  elif len(intf.get('neighbors',[])) == 1:
    intf[proto].network_type = p2p                  # Network type not specified, set it for P2P links

  return None

# Remove routing protocol data from an interface with "external" role
#
def external(intf: Box, proto: str) -> bool:
  if intf.get('role','') == "external":
    intf.pop(proto,None)
    return True

  if proto in intf and isinstance(intf[proto],bool) and not intf[proto]:        # Disable IGP on an interface by setting it to False
    intf.pop(proto,None)
    return True

  return False

# Figure out whether an interface is truly a stub interface
#
# This routing is called to figure out what exactly a link with a 'stub'
# role is. When used by IGP modules, it checks whether there's an adjacent
# node running the same IGP (in which case the interface should not be passive).
# When used by BGP, it just checks whether a neighbor is a daemon

def is_true_stub(intf: Box, topology: Box, proto: str = '') -> bool:
  for n in intf.get('neighbors',[]):                        # Iterate over the neighbors
    ndata = topology.nodes[n.node]                          # Find the neighbor details
    if proto:                                               # IGP check
      if proto in ndata.get('module',[]):                   # Is the neighbor running the same IGP?
        return False                                        # ... then the interface is not a true stub
    else:
      if ndata.get('_daemon',False) or ndata.get('role','') != 'host':
        return False                                        # BGP check -- is the neighbor a daemon or a router?

  return True                                               # Found no exceptions, must be a true stub

'''
Figure out whether an IGP interface should be passive

* The proto.passive flag is set
* The link role is 'passive' (set manually) or the link is a stub link (single node attached to it)
* The link is a stub link (so it has at most one non-host attached)
  and other devices on the link are not running the same protocol (so no daemons)

Also, report an error if we have an explicit 'passive' flag used on a device that does not support
passive interfaces (most other 'passive' use cases are primarily cosmetic).
'''
def passive(
      intf: Box,                                            # Interface to check
      proto: str,                                           # Routing protocol to check
      topology: Box,                                        # We need reference to full topology to check for full stub
      features: typing.Optional[Box] = None,                # Optional for protocols that have problems with 'passive' interfaces
      ndata: typing.Optional[Box] = None) -> None:          # ... and node data in case we have to report an error

  if 'passive' in intf[proto]:                              # Explicit 'passive' flag
    intf[proto].passive = bool(intf[proto].passive)         # ... turn it into bool (just in case)
    if features and ndata:
      p_flag = features.get(f'{proto}.passive',None)
      if p_flag is False:
        log.error(
          f'Device {ndata.device} (node {ndata.name}) does not support passive {proto} interfaces',
          log.IncorrectType,
          proto)
    return

  role = intf.get('role',"")
  if role in ["passive","external"] or intf.type == 'stub': # Passive/external role or stub link ==> must be passive
    intf[proto].passive = True
    return

  if role != "stub":                                        # Not a stub role ==> not passive
    intf[proto].passive = False
    return

  # And now for the gray area. The only signal we have is link role set to stub, which implies
  # there's at most one router attached to the link. However, there might be host daemons
  # attached to it, so we have to do further checks
  #
  # Note that we cannot fix this by setting link role to something else, as the 'stub' role
  # triggers the generation of default gateway which is used for default routing on daemons
  intf[proto].passive = is_true_stub(intf,topology,proto)

# Get a router ID prefix from the router_id pool
#
def get_router_id_prefix(node: Box, proto: str, pools: Box, use_id: bool = True) -> typing.Optional[Box]:
  if not pools.router_id:
    log.error(
      f'Cannot create a router ID for protocol {proto} on node {node.name}: router_id addressing pool is not defined',
      log.MissingValue,
      proto)
    return None

  pool = 'router_id'
  pfx = addressing.get(pools,[ pool ],node.id if use_id else None)
  if not pfx:
    log.error(
      f'Cannot create a router ID prefix from {pool} pool for protocol {proto} on node {node.name}',
      log.IncorrectValue,
      proto)
    return None

  if not pfx.get('ipv4',None):
    log.error(
      f'{pool} pool did not return a usable IPv4 address to use as router ID for protocol {proto} on node {node.name}',
      log.IncorrectValue,
      proto)
    return None

  return pfx

# Create router ID if needed
#
def router_id(node: Box, proto: str, pools: Box) -> None:
  if 'router_id' in node.get(proto,{}):       # User-configured per-protocol router ID, get out of here
    try:
      node[proto].router_id = str(netaddr.IPAddress(node[proto].router_id).ipv4())
    except Exception as ex:
      log.error(
        f'{proto} router_id "{node[proto].router_id}" specified on node {node.name} is not an IPv4 address',
        log.IncorrectValue,
        proto)
    return

  if 'router_id' in node:                     # Node has a configured router ID, copy it and get out
    try:
      node.router_id = str(netaddr.IPAddress(node.router_id).ipv4())
      node[proto].router_id = node.router_id
    except Exception as ex:
      log.error(
        f'router_id "{node.router_id}" specified on node {node.name} is not an IPv4 address',
        log.IncorrectValue,
        proto)
    return

  if 'ipv4' in node.get('loopback',{}):       # Do we have IPv4 address on the loopback? If so, use it as router ID
    node[proto].router_id = str(netaddr.IPNetwork(node.loopback.ipv4).ip)
    return

  pfx = get_router_id_prefix(node,proto,pools)
  if not pfx:
    return

  node.router_id = str(netaddr.IPNetwork(pfx['ipv4']).ip)
  node[proto].router_id = node.router_id

#
# remove_vrf_interfaces -- remove interfaces in a VRF from a routing process that is not VRF-aware
#
def remove_vrf_interfaces(node: Box, proto: str) -> None:
  for l in node.interfaces:
    if proto in l and 'vrf' in l:
      l.pop(proto,None)

#
# build_vrf_interface_list -- copy VRF interfaces into VRF definition
#
def build_vrf_interface_list(node: Box, proto: str, topology: Box) -> None:
  for l in node.interfaces:
    if proto in l and 'vrf' in l:
      if node.vrfs[l.vrf][proto] is True:                                   # Handle 'force' the protocol by setting it to True
        node.vrfs[l.vrf][proto] = { 'active': True }
      elif node.vrfs[l.vrf][proto] is False:                                # Skip protocols disabled on VRF level
        l.pop(proto,None)
        continue
      if not 'interfaces' in node.vrfs[l.vrf][proto]:                       # Start with an empty interface list
        node.vrfs[l.vrf][proto].interfaces = []
      if not 'active' in node.vrfs[l.vrf][proto]:                           # Assume there are no IGP neighbors in this VRF
        node.vrfs[l.vrf][proto].active = False
      node.vrfs[l.vrf][proto] = node[proto] + node.vrfs[l.vrf][proto]       # Add node IGP parameters to VRF IGP parameters
      node.vrfs[l.vrf][proto].interfaces.append(data.get_box(l))            # Append a copy of the interface data
      l.pop(proto,None)                                                     # ... and remove global IGP parameters from interface
                                                                            # Next we need to find if the VRF instance of IGP matters
      for neighbor in l.neighbors:                                          # ... iterate over the list of neighbors
        n_data = topology.nodes[neighbor.node]
        if proto in n_data.get('module',[]):                                # ... and check if at least one of them uses the IGP
          node.vrfs[l.vrf][proto].active = True
                                                                            # Cleanup IGP data
  for vdata in node.get('vrfs',{}).values():                                # ... iterate over the list of VRFs
    try:
      proto_active = vdata.get(f'{proto}.active',False)                     # Get the IGP data for the VRF
    except:                                                                 # ... assume 'not active' if get fails
      proto_active = False
    if not proto_active:                                                    # If there's no record of active IGP neighbors
      vdata.pop(proto,None)                                                 # ... remove the VRF IGP instance

#
# remove_unaddressed_intf -- remove all interfaces without IPv4 or IPv6 address from IGP
#
# This routing should be called BEFORE build_vrf_interface_list to ensure the interfaces without any usable
# L3 address are not copied into VRF interface list
#

def remove_unaddressed_intf(node: Box, proto: str) -> None:
  for intf in node.interfaces:
    if proto in intf:
      if not any(af in intf for af in ('ipv4','ipv6','unnumbered')):        # Do we have at least some addressing on the interface?
        intf.pop(proto,None)                                                # Nope, no need to run IGP on that interface
#
# remove_unused_igp -- remove IGP module if it's not configured on any interface
#
def remove_unused_igp(node: Box, proto: str, warning: bool = False) -> None:
  if not any(proto in ifdata for ifdata in node.interfaces):                # Is protocol configured on any non-loopback interface?
    node.pop(proto,None)                                                    # ... no, remove protocol data from node

  if proto in node and 'af' in node[proto] and node[proto].af:              # Is at least one global AF active for the protocol?
    return                                                                  # ... OK, we're good

  for vdata in node.get('vrfs',{}).values():                                # Is protocol active in at least one VRF?
    if proto in vdata:
      return                                                                # ... OK, we're good

  node.module = [ m for m in node.module if m != proto ]                    # Makes no sense to keep it, remove the config module
  if warning:
    log.error(
      f'{node.name} does not use {proto} on any non-loopback interface or VRF',
      more_hints=f'It has been removed from the list of modules active on {node.name}',
      category=Warning,
      module=proto)
#
# remove_vrf_routing_blocks -- remove 'proto: False' VRF settings
#

def remove_vrf_routing_blocks(node: Box, proto: str) -> None:
  if not 'vrfs' in node:                                                    # No VRFs, no work
    return

  for vdata in node.vrfs.values():
    if not proto in vdata:                                                  # This VRFs doesn't care about our protocol, move on
      continue
    if not vdata[proto] is False:                                           # Not a false flag
      continue

    vdata.pop(proto,None)                                                   # Got rid of the false flag

"""
check_vrf_support: Check whether a node supports the desired routing protocol in a VRF

Inputs:
* Node to check
* netlab protocol (ospf / bgp)
* protocol address family (ipv4 for ospfv2, ipv6 for ospfv3)
* feature to check in device features
* topology (to get defaults)
"""
def check_vrf_protocol_support(
      node: Box,
      proto: str,
      af: typing.Optional[str],
      feature: str,
      topology: Box) -> None:
  if not 'vrfs' in node:                          # No VRFs in the current node, nothing to check
    return
  
  for v_name,v_data in node.vrfs.items():         # Iterate over VRFs
    if not proto in v_data:                       # Are we running the target protocol in the VRF?
      continue
    if af and not af in v_data.af:                # Does the VRF use the target address family?
      continue

    # We found the protocol to check in the current VRF, time to check device features
    d_feature = devices.get_device_features(node,topology.defaults)
    if not d_feature.get(f'vrf.{feature}',False): # Does the device support the target protocol/AF combo?
      log.error(
        f'Device {node.device} (node {node.name}) does not support {feature} in VRFs (found in VRF {v_name})',
        category=log.IncorrectValue,
        module=proto)
      return

"""
get_remote_cp_endpoint: find the remote control-plane endpoint

Return loopback interface or the first physical interface
"""
def get_remote_cp_endpoint(n: Box) -> Box:
  if 'loopback' in n and n.get('role') != 'host':           # The node has loopback and is not a host
    return n.loopback                                       # ... can't use loopback if the node has no routing

  if n.interfaces:                                          # Hope the node has at least one usable interface
    return n.interfaces[0]                                  # ... if it does, return that

  return data.get_empty_box()                               # Otherwise return an empty box

"""
get_router_id_blacklist: As we generate router IDs in various ways, we have no way of
figuring out which ones were already used. The only bruteforce method is thus to build
a list of router ID per protocol
"""
def get_router_id_blacklist(topology: Box, proto: str) -> list:
  blist = []
  for ndata in topology.nodes.values():                     # Iterate over all nodes
    blist.append(ndata.get(f'{proto}.router_id',None))      # Blindly add router ID from global proto instance
    for vdata in ndata.get('vrfs',{}).values():
      blist.append(vdata.get(f'{proto}.router_id',None))    # ... and from all VRFs

  return [ x for x in blist if x is not None ]              # Obviously some of those values do not exist
                                                            # ... so we have to filter them out

"""
get_unique_router_ids: change router IDs in VRF routing protocols for devices that want
to have a unique router_id per routing protocol instance (Cisco IOSv)

This could be part of IOSv quirks, but we might have other devices with similarly weird
behavior
"""
def get_unique_router_ids(node: Box, proto: str, topology: Box) -> None:
  if 'vrfs' not in node:
    return

  rid_list: list = []                                       # Keep track of on-device RIDs
  rid_blacklist: list = []                                  # ... and a global list of already-used RIDs
  if proto in node:
    rid_list.append(node.get(f'{proto}.router_id'))         # The node is running a global copy of the protocol

  for vname,vdata in node.vrfs.items():                     # Now iterate over all VRFs
    if proto not in vdata:                                  # ... protocol not running in VRF, move on
      continue
    rid = vdata.get(f'{proto}.router_id')
    if rid not in rid_list:                                 # VRF router ID is unique, move on
      rid_list.append(rid)
      continue

    if not rid_blacklist:                                   # Get the global black lisf if needed
      rid_blacklist = get_router_id_blacklist(topology,proto)
      print(f'blacklist: {rid_blacklist}')

    while True:                                             # Try to get the next router ID from the pool
      rid_pfx = get_router_id_prefix(node,proto,topology.pools,use_id=False)
      if not rid_pfx:
        break
      router_id = str(netaddr.IPNetwork(rid_pfx['ipv4']).ip)
      if router_id not in rid_blacklist:                    # ... until it's not in the blacklist
        break

    if rid_pfx:                                             # If we have a prefix, we also have a RID
      vdata[proto].router_id = router_id                    # ... so set it and report the change
      log.error(
        f'router ID for VRF {vname} on node {node.name} was changed from {rid} to {vdata[proto].router_id}',
        category=Warning,
        module=proto,
        more_hints=f'Device {node.device} requires a unique router ID for each {proto} instance')
    else:                                                   # Ran out of RID pool, report another error
      log.error(
        f'Cannot change router ID for VRF {vname} on node {node.name}',
        category=Warning,
        module=proto)
