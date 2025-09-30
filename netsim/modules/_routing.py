"""
Routing Protocol utility functions:

* network_type: set IGP network type on a link. Used by OSPF and IS-IS
* routing_af: set routing protocol address families for a node
* external: return True is an interface is an external interface, and removes IGP-related parameters from the interface
* passive: set IGP 'passive' flag on an interface
"""

import typing

from box import Box

from .. import data
from ..augment import addressing, devices
from ..data import global_vars
from ..utils import log
from ..utils import routing as _rp_utils
from . import get_effective_module_attribute
from .routing.policy import check_routing_policy, import_routing_policy


# Build routing protocol address families
#
# * If the address families are not set, calculate them based on interface address families
# * Otherwise parse and validate the AF attribute
#
# Please note that this function could be called with node data (for global routing instance)
# or VRF data (acting as node data) for VRF routing instances
#
def routing_af(
      node: Box,                                      # Could also be VRF data
      proto: str,                                     # IGP we're checking
      n_name: typing.Optional[str] = None,            # Name of the object (default: node name)
      is_vrf: bool = False,                           # Are we dealing with a VRF?
      features: typing.Optional[Box] = None) -> None: # And finally, the device features

  if n_name is None:
    n_name = 'node {node.name}'
  if 'af' in node[proto] and node[proto].af is None:
    node[proto].pop('af',None)

  if not 'af' in node[proto]:                         # No configured AF attribute, calculate it
    for af in ['ipv4','ipv6']:                        # Process the loopback interface
      lb_data = node.get('loopback',{})               # Fetch the loopback interface info
      if isinstance(lb_data,Box):                     # ... watch out for bool values
        if af in lb_data:                             # Address family enabled on loopback?
          node[proto].af[af] = True                   # ... we need it in the routing protocol
          continue

      # Scan all interfaces -- they could be in node.interfaces or vrf_data.proto.interfaces
      if_list = node[proto].get('interfaces',[]) if is_vrf else node.get('interfaces',[])
      for l in if_list:
        if 'vrf' in l and not is_vrf:                 # Skip VRF interfaces when processing global routing instance
          continue                                    # VRF instances will only have correct VRF interfaces anyway

        # Do we have AF enabled on the global- or VRF interface
        if proto in l and (af in l or af in l.get('dhcp.client',{})):
          node[proto].af[af] = True                   # Found the AF - we need it in the routing protocol
          continue

  p_features = features.get(proto,{}) if features else {}

  for af in ['ipv4','ipv6']:                          # Remove unused address families
    if not node[proto].af.get(af,False):
      node[proto].af.pop(af,False)
      continue

    if af in p_features and p_features[af] is False:
      log.error(
        f'{n_name} cannot run {proto} on {af}',
        log.IncorrectValue,
        proto)

# After parsing/building the IGP AF structure and offloading VRF interfaces into VRF data
# structure, recheck the interface status. If there's no match between interface AF and IGP AF,
# remove IGP from the interface

def check_interface_af(node: Box, proto: str) -> None:
  for vrf_proto in routing_protocol_data(node,proto):
    interfaces = vrf_proto.get('interfaces',node.interfaces)                # Get VRF IGP interfaces or global intf
    if 'af' not in vrf_proto:                                               # Is this IGP instance limited by AFs?
      continue
    AF_mismatch = False
    for intf in interfaces:
      if proto not in intf:                                                 # IGP not active on this interface
        continue
      if any((intf.get(af,False) or intf.get(f'dhcp.client.{af}',False))
              and vrf_proto.af.get(af,False)
                for af in log.AF_LIST):                                     # Do we have at least one matching AF?
        continue
      intf.pop(proto,None)                                                  # No, remove IGP from the interface
      AF_mismatch = True                                                    # And remember we did that

    if AF_mismatch and 'interfaces' in vrf_proto:                           # Do we have to rebuild VRF intf list?
      vrf_proto.interfaces = [ intf for intf in vrf_proto.interfaces if proto in intf ]

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

'''
Add IGP information to the loopback interface to enable the templates to use netlab_interfaces
'''
def add_loopback_igp(node: Box, proto: str, topology: Box) -> None:
  if 'loopback' not in node:                                # Node working in host mode, no loopback
    return

  if node.loopback.get(proto) is False:
    return

  d_feature = devices.get_device_features(node,topology.defaults)
  lb_data = d_feature[proto].get('loopback',{})             # Get device-specific loopback info (if present)
  if not isinstance(lb_data,Box):                           # Sanity check
    log.fatal(f'defaults.devices.{node.device}.features.{proto}.loopback must be a dictionary')

  node.loopback[proto] = lb_data + node.loopback[proto]     # Merge device LB info with whatever is already on LB
                                                            # Note that an empty box is created on first reference
  if 'passive' not in node.loopback[proto]:                 # Finally, many templates expect 'passive' to be present
    node.loopback[proto].passive = False                    # ... so add a bogus 'not passive' flag if needed

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
      node[proto].router_id = _rp_utils.get_address(node[proto].router_id)
    except Exception as ex:
      log.error(
        f'{proto} router_id "{node[proto].router_id}" specified for {proto} on node {node.name} is not an IPv4 address',
        more_data=str(ex),
        category=log.IncorrectValue,
        module=proto)
    return

  if 'router_id' in node:                     # Node has a configured router ID, copy it and get out
    try:
      node.router_id = _rp_utils.get_address(node.router_id)
      node[proto].router_id = node.router_id
    except Exception as ex:
      log.error(
        f'router_id "{node.router_id}" specified on node {node.name} is not an IPv4 address',
        more_data=str(ex),
        category=log.IncorrectValue,
        module=proto)
    return

  if 'ipv4' in node.get('loopback',{}):       # Do we have IPv4 address on the loopback? If so, use it as router ID
    node[proto].router_id = _rp_utils.get_intf_address(node.loopback.ipv4)
    return

  pfx = get_router_id_prefix(node,proto,pools)
  if not pfx:
    return

  node.router_id = _rp_utils.get_intf_address(pfx['ipv4'])
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
def build_vrf_interface_list(
      node: Box,
      proto: str,
      topology: Box,
      vrf_unnumbered_check: bool = True) -> None:                     # Check the source IP VRF for IPv4 unnumbereds
  
  unnum_err_list = data.get_empty_box()
  features = devices.get_device_features(node,topology.defaults)

  for l in node.interfaces:
    if proto not in l:                                                # Not running the protocol on the interface?
      continue
    if 'vrf' not in l:                                                # Interface not in a VRF?
      continue
    if l.get('_phantom_link',False):                                  # Is this an interface on a phantom link?
      continue                                                        # Skip it, the interface will be removed anyway
    if node.vrfs[l.vrf][proto] is True:                               # Handle 'force' the protocol by setting it to True
      node.vrfs[l.vrf][proto] = { 'active': True }
    elif node.vrfs[l.vrf][proto] is False:                            # Skip protocols disabled on VRF level
      l.pop(proto,None)
      continue
    if not 'active' in node.vrfs[l.vrf][proto]:                       # Assume there are no IGP neighbors in this VRF
      node.vrfs[l.vrf][proto].active = False
    node.vrfs[l.vrf][proto] = node[proto] + node.vrfs[l.vrf][proto]   # Add node IGP parameters to VRF IGP parameters
    data.append_to_list(
      node.vrfs[l.vrf][proto],
      list_name='interfaces',
      item=data.get_box(l))                                           # Append a copy of the interface data
    if vrf_unnumbered_check and \
        l.get('ipv4',None) is True and \
        l.get('_parent_vrf',None) != l.vrf:                           # Have to check the loopback source VRF?
      data.append_to_list(unnum_err_list,l.vrf,l.ifname)              # ... remember we failed

    l.pop(proto,None)                                                 # Finally, remove global IGP parameters from interface
                                                                      # Next we need to find if the VRF instance of IGP matters
    for neighbor in l.neighbors:                                      # ... iterate over the list of neighbors
      n_data = topology.nodes[neighbor.node]
      if proto in n_data.get('module',[]):                            # ... and check if at least one of them uses the IGP
        for af in ['ipv4','ipv6']:                                    # ... and has at least one AF in common
          if af in l and af in neighbor:                              # ... with our interface
            node.vrfs[l.vrf][proto].active = True                     # Found one? Let's keep the routing protocol active

  # Time to cleanup IGP data
  for vname,vdata in node.get('vrfs',{}).items():                     # ... iterate over the list of VRFs
    proto_active = isinstance(vdata[proto],Box) \
                   and vdata[proto].get(f'active',False)              # Get the IGP active status for the VRF
    if not proto_active:                                              # If there's no record of active IGP neighbors
      remove_vrf_imports(node,vname,vdata,proto)                      # Remove all mentions of the IGP imports
      vdata.pop(proto,None)                                           # ... remove the VRF IGP instance
      continue

    # IGP protocol is active in the VRF
    if unnum_err_list[vname]:                                         # Do we have unnumbered errors?
      log.error(
        f"VRF {vname} on {node.name} has unnumbered interface(s) running {proto} without a VRF loopback",
        category=log.MissingDependency,
        module="vrf",
        more_data=f"Used on interface(s) {','.join(unnum_err_list[vname])}")

    routing_af(vdata,proto,f'VRF {vname} on {node.name}',is_vrf=True,features=features)

#
# remove_unaddressed_intf -- remove all interfaces without IPv4 or IPv6 address from IGP
#
# This routing should be called BEFORE build_vrf_interface_list to ensure the interfaces without any usable
# L3 address are not copied into VRF interface list
#

def remove_unaddressed_intf(node: Box, proto: str) -> None:
  for intf in node.interfaces:
    if proto in intf:
      if not any(af in intf or af in intf.get('dhcp.client',{})
                   for af in ('ipv4','ipv6')):                              # Do we have at least some addressing on the interface?
        intf.pop(proto,None)                                                # Nope, no need to run IGP on that interface
#
# remove_unused_igp -- remove IGP module if it's not configured on any interface
#
def remove_unused_igp(node: Box, proto: str, remove_module: bool = True) -> bool:
  if 'loopback' in node and node.loopback.get(proto) is False:              # Deal with IGP disabled on the loopback interface
    node.loopback.pop(proto,None)

  if not any(proto in ifdata for ifdata in node.interfaces):                # Is protocol configured on any non-loopback interface?
    node.pop(proto,None)                                                    # ... no, remove protocol data from node
    if isinstance(node.get('loopback',None),Box):                           # Do we have a usable loopback interface on the node?
      node.loopback.pop(proto,None)                                         # ... remove protocol data from loopback

  if proto in node and 'af' in node[proto] and node[proto].af:              # Is at least one global AF active for the protocol?
    return False                                                            # ... OK, we're good

  for vdata in node.get('vrfs',{}).values():                                # Is protocol active in at least one VRF?
    if proto in vdata and vdata[proto].get('interfaces',[]):                # ... and at least on one interface?
      return False                                                          # ... OK, we're good

  if not remove_module:                                                     # Did the caller ask us to keep the module
    return True                                                             # ... module list intact?

  node.module = [ m for m in node.module if m != proto ]                    # Not used, remove the config module
  log.warning(
    text=f'{node.name} does not use {proto} on any non-loopback interface or VRF',
    more_hints=f'It has been removed from the list of modules active on {node.name}',
    flag='inactive',
    module=proto)
    
  return True

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
      v_data[proto].af.pop(af,None)               # Make sure the AF is not set in VRF routing protocol data
      continue

    # We found the protocol to check in the current VRF, time to check device features
    d_feature = devices.get_device_features(node,topology.defaults)
    if not d_feature.get(f'vrf.{feature}',False): # Does the device support the target protocol/AF combo?
      f_name = feature if feature != proto else f'{proto} for {af}'
      log.error(
        f'Device {node.device} (node {node.name}) does not support {f_name} in VRFs (found in VRF {v_name})',
        category=log.IncorrectValue,
        module=proto)
      return

"""
check_intf_support -- check device support for optional interface parameters
"""
def check_intf_support(node: Box, proto: str, topology: Box) -> bool:
  attr = topology.defaults[proto].attributes.get('intf_optional',None)
  if attr is None:                                # This RP has no optional interface attributes
    return True

  features = devices.get_device_features(node,topology.defaults)[proto]
  err_list = data.get_empty_box()

  # Iterate over interfaces using the specified IGP
  #
  for intf in _rp_utils.igp_interfaces(node,proto):
    for kw in intf.get(proto,{}).keys():          # Iterate over interface protocol parameters
      if kw not in attr:                          # Not an optional attribute, move on
        continue
      if kw not in features:                      # Optional attribute, but not supported => add error info
        data.append_to_list(err_list,kw,f'interface {intf.ifname} ({intf.name})')

  if not err_list:                                # No errors found, we're done
    return True

  for kw in err_list.keys():                      # Iterate over collected error data
    log.error(                                    # ... and report every unsupported attribute
      f'Device {node.device} (node {node.name}) does not support {proto} interface parameter {kw}',
      category=log.IncorrectAttr,
      module=proto,
      more_data=err_list[kw])                     # ... together with the list of interfaces where it was found

  return False

"""
get_remote_cp_endpoint: find the remote control-plane endpoint

Return loopback interface or a physical interface, preferring intra-AS over external over VRF interfaces
"""
def get_remote_cp_endpoint(n: Box) -> Box:
  if 'loopback' in n and n.get('role') != 'host':           # The node has loopback and is not a host
    return n.loopback                                       # ... can't use loopback if the node has no routing

  topology = global_vars.get_topology() or data.get_empty_box()
  EBGP_ROLE = get_effective_module_attribute(
                path='bgp.ebgp_role',
                topology=topology,
                defaults=topology.defaults) or 'external'

  # Remember the interfaces we found in order of preference
  intf_options: dict = { 'internal': None, 'external': None, 'vrf': None }

  for intf in n.interfaces:                                 # Iterate over all interfaces
    intf_type = 'vrf' if 'vrf' in intf else 'external' if intf.get('role',None) == EBGP_ROLE else 'internal'
    if intf_options[intf_type] is None:                     # Do we already have an interface of this type?
      intf_options[intf_type] = intf                        # ... nope, remember it

  # Collect the list of all relevant interfaces
  best_intf = [ intf for intf in intf_options.values() if intf is not None ]

  if best_intf:                                             # Did we find at least one relevant interface?
    return best_intf[0]                                     # ... return the best one
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

    while True:                                             # Try to get the next router ID from the pool
      rid_pfx = get_router_id_prefix(node,proto,topology.pools,use_id=False)
      if not rid_pfx:
        break
      router_id = _rp_utils.get_intf_address(rid_pfx['ipv4'])
      if router_id not in rid_blacklist:                    # ... until it's not in the blacklist
        break

    if rid_pfx:                                             # If we have a prefix, we also have a RID
      vdata[proto].router_id = router_id                    # ... so set it and report the change
      log.warning(
        text=f'router ID for VRF {vname} on node {node.name} was changed from {rid} to {vdata[proto].router_id}',
        module=proto,
        more_hints=f'Device {node.device} requires a unique router ID for each {proto} instance',
        flag='changed_id')
    else:                                                   # Ran out of RID pool, report another error
      log.warning(
        text=f'Cannot change router ID for VRF {vname} on node {node.name}',
        module=proto)

"""
is_vrf_protocol: Check if a protocol runs in the current VRF
"""
def is_vrf_protocol(node: Box, vdata: Box, s_proto: str) -> bool:
  if s_proto in ['connected','static']:                     # Pseudo-protocols are always OK
    return True
  if s_proto in vdata:                                      # VRF has protocol-specific data
    return True
  if s_proto == 'bgp' and node.get('bgp.as',None):          # BGP is special; VRF import/export depends on it
    return True
  return False                                              # Found no good reason to import from this protocol

"""
node_add_routing_policy: Add a routing policy to a node (includes import from global and sanity checks)
"""
def node_add_routing_policy(r_policy: typing.Any, node: Box, topology: Box) -> None:
  if not r_policy or not isinstance(r_policy,str):
    return

  if import_routing_policy(r_policy,'policy',node,topology):          # Did we import the requested policy?
    check_routing_policy(r_policy,'policy',node,topology)             # ... if so, it's time for a sanity check

"""
check_import_request: Check whether a route import request is valid

* Does the target protocol support route import?
* Is the source protocol active on the device?
* If the import uses a routing policy, is it valid, and does the node use routing module?
"""
def check_import_request(
      proto: str,
      node: Box,
      rdata: Box,
      topology: Box,
      features: Box) -> None:

  f_import = features.get(f'{proto}.import',[])
  if not features.get(f'{proto}.import',False):             # Does the device support imports into this protocol?
    log.error(
      f'Device {node.device} (node {node.name}) does not support route import into {proto}',
      category=log.IncorrectValue,
      module=proto)
    return

  i_dict = rdata['import']                                  # Use a temporary variable to shorten the code
  for s_proto in list(i_dict.keys()):                       # Iterate over the source protocol(s)
    if isinstance(f_import,list) and s_proto not in f_import:
      log.error(
        f'Device {node.device} (node {node.name}) cannot import {s_proto} routes into {proto}',
        category=log.IncorrectValue,
        module=proto)
      continue
    i_data = i_dict[s_proto]
    if i_data is False:                                     # Remove requests to disable route import 
      i_dict.pop(s_proto,None)                              # ... needed to disable group-wide import
      continue
    if i_data is True:                                      # Change 'true' into an empty dictionary
      rdata['import'][s_proto] = {}

    if not s_proto in node.module and s_proto not in ['connected','static']:
      log.error(                                            # Source protocol not active on the node ==> yell
        f'Node {node.name}: cannot import routes from {s_proto} which is not running on the box',
        category=log.IncorrectValue,
        module=proto)
      continue

    if s_proto == proto:                                    # Cannot redistribute a protocol into itself
      log.error(
        f'Node {node.name}: cannot {s_proto} routes into {proto}',
        more_hints=['Route import works between different protocols or from connected subnets'],
        category=log.IncorrectValue,
        module=proto)
      continue

    # Add an import routing policy if needed
    i_policy = i_dict.get(f'{s_proto}.policy',None)
    if i_policy:
      if 'no_policy' in f_import:
        log.error(
          f'Device {node.device} (node {node.name}) cannot use routing policies ' + \
          f'on route imports ({s_proto} => {proto}, policy {i_policy})',
          category=log.IncorrectValue,
          module=proto)
        break
      else:
        node_add_routing_policy(i_dict.get(f'{s_proto}.policy'),node,topology)

  if 'ripv2' in i_dict:                                     # Finally, replace RIPv2 with RIP
    i_dict.rip = i_dict.ripv2
    i_dict.pop('ripv2',None)

"""
process_imports: Process route redistribution requests in global routing table and VRFs
"""
def process_imports(node: Box, proto: str, topology: Box, vrf_list: list) -> None:
  features = devices.get_device_features(node,topology.defaults)      # We'll need device features for sanity checks
  if node.get(f'{proto}.import',{}):                                  # Do we have global import request?
    check_import_request(proto,node,node[proto],topology,features)    # ... check it!
  
  i_feature = features.get(f'{proto}.import',[])                      # Is the protocol route import VRF-aware?
  vrf_aware = i_feature is True or isinstance(i_feature,list) \
              and 'vrf' in i_feature

  for vname,vdata in node.get('vrfs',{}).items():                     # OK, have to check all VRFs
    if not is_vrf_protocol(node,vdata,proto):                         # Is VRF using this protocol?
      continue                                                        # ...no, move on

    if 'import' not in vdata[proto]:                                  # If the user did not configure VRF import...
      if not vrf_aware:                                               # This device/protocol combination is not
        continue                                                      # ... VRF-aware, move on
      if features.get(f'{proto}.import',False):                       # Does the device supports imports?
        for s_proto in vrf_list:                                      # ... create a default import dictionary
          #
          # Import suggested source protocol record if the source protocol is in VRF
          # or if the destination protocol is BGP and the source protocol is present
          # on the device (in which case the IGP module will remove the VRF import)
          #
          do_import = is_vrf_protocol(node,vdata,s_proto) or \
                      (proto == 'bgp' and s_proto in node)
          if do_import:
            sp_name = 'rip' if s_proto == 'ripv2' else s_proto        # Use 'rip' for RIPv2 in final data structures
            vdata[proto]['import'][sp_name] = { 'auto': True }        # ... mark import as auto-generated
    else:                                                             # Explicit import configuration
      if vrf_aware:                                                   # ... if the protocol is VRF-aware check it
        check_import_request(proto,node,vdata[proto],topology,features)
      else:
        log.error(
          f'Route import from {s_proto} to {proto} on node {node.name} (device {node.device}) is not VRF-aware',
          category=log.IncorrectValue,
          module=proto)

"""
remove_vrf_imports: remove incorrect VRF imports

When creating VRF route imports for BGP, the IGP data could still be present in the VRF
even if the VRF does not use that IGP. The IGP data is removed in the node_post_transform
IGP code, but that's too late for BGP (BGP has to run before VRF which has to run before IGP).

The only way to handle that circular dependency (without introducing another pass through the
data) is to call a cleanup routine whenever an IGP is removed from the VRF. The cleanup routine
has to go through all VRF data, detect imports, remove them, and raise an error if needed.
"""
def remove_vrf_imports(node: Box, vname: str, vdata: Box, proto: str) -> None:
  for rp in ['bgp','ospf','isis','ripv2','eigrp']:                    # Iterate over all routing protocols
    if not rp in vdata:                                               # RP is (no longer?) used in the VRF
      continue
    if not isinstance(vdata[rp],Box):                                 # Not a full-blown RP data structure
      continue
    if not 'import' in vdata[rp]:                                     # RP is present in VRF but has no imports
      continue

    rp_import = vdata[rp]['import']                                   # Get a pointer to import dictionary
    if proto not in rp_import:                                        # Our protocol did not make it into imports
      continue
    if rp_import[proto].get('auto',False):                            # Was it an auto-import?
      rp_import.pop(proto,None)                                       # Yes, we can just remove it
    else:
      log.error(
        f'Cannot import {proto} routes into {rp} in VRF {vname} on node {node.name}: {proto} is not active in that VRF',
        category=log.IncorrectValue,
        module=rp)

"""
process_default_route: Perform default route processing

* Turn bool into dict
* Check feature support
"""
def default_route_adjust(
      node: Box,
      vdata: Box,
      proto: str,
      topology: Box,
      features: Box,
      vname: str) -> None:
  if proto not in vdata:                          # Protocol not active in current VRF
    return
  if 'default' not in vdata[proto]:               # No default route spec for current protocol
    return

  if vdata[proto].default is False:               # A request to disable default route?
    vdata[proto].pop('default',None)
    return

  if vdata[proto].default is True:                # For consistency and template simplicity...
    vdata[proto].default = { 'enabled': True }    # ... turn 'default: True' into a dictionary

  f_default = features.get(f'{proto}.default',None)
  if not f_default:
    log.error(
      f'Device {node.device} (node {node.name}) cannot originate {proto} default route in {vname}',
      category=log.IncorrectValue,
      module=proto)
    return
  
  if 'policy' in vdata[proto].default:            # Add default route origination routing policy if needed
    if isinstance(f_default,Box) and f_default.policy:
      node_add_routing_policy(vdata[proto].default.policy,node,topology)
    else:                                         # ... but only if the device supports taht
      log.error(
        f'Device {node.device} (node {node.name}) cannot use a route-map when originating {proto} default route in {vname}',
        category=log.IncorrectValue,
        module=proto)


def process_default_route(node: Box, proto: str, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)
  default_route_adjust(
    node=node,
    vdata=node,
    proto=proto,
    topology=topology,
    features=features,
    vname='global routing table')
  
  for vname,vdata in node.get('vrfs',{}).items():
    default_route_adjust(
      node=node,
      vdata=vdata,
      proto=proto,
      topology=topology,
      features=features,
      vname=f'VRF {vname}')

"""
igp_post_transform: Perform common IGP transformation/cleanup tasks

* Remove IGP data from interfaces with no usable IP addresses
* Move IGP-enabled VRF interfaces into VRF dictionary
* Calculate address families for global instance and VRFs
* Propagate node attributes (IGP specific, callback)
* Remove IGP module if there are no IGP-enabled global or VRF interfaces
* Process imports into IGP
"""

def igp_post_transform(
      node: Box,
      topology: Box,
      proto: str,
      vrf_aware: bool = False,
      vrf_unnumbered_check: bool = True,
      propagate: typing.Optional[typing.Callable] = None) -> None:

  features = devices.get_device_features(node,topology.defaults)

  remove_unaddressed_intf(node,proto)
  if vrf_aware:
    build_vrf_interface_list(node,proto,topology,vrf_unnumbered_check)
  else:
    remove_vrf_interfaces(node,proto)

  routing_af(node,proto,f'node {node.name}',features=features)
  if vrf_aware:
    remove_vrf_routing_blocks(node,proto)
  
  if propagate is not None:
    propagate(node,topology)
  
  add_loopback_igp(node,proto,topology)
  check_interface_af(node,proto)
  if remove_unused_igp(node,proto):
    return

  process_imports(node,proto,topology,['bgp','connected'])
  process_default_route(node,proto,topology)

"""
routing_protocol_data: Given a node and a protocol name, returns the global protocol data
and any VRF instances

You can use this generator to iterate over all routing protocol instances without going through
the "global first, then VRFs" logic on your own
"""
def routing_protocol_data(node: Box, proto: str) -> typing.Generator:
  if isinstance(node.get(proto,None),Box):
    yield node[proto]

  for vname,vdata in node.get('vrfs',{}).items():
    if isinstance(vdata.get(proto,None),Box):
      yield vdata[proto]

"""
routing_protocol_interfaces: Given a node and a protocol name, returns the
interface data structures for global and VRF interfaces running the specified
protocol

You can use this generator to iterate over all interface instances without going
through the "global first, then VRFs" logic on your own
"""
def routing_protocol_interfaces(node: Box, proto: str) -> typing.Generator:
  for intf in node.interfaces:
    if proto in intf:
      yield intf

  for vname,vdata in node.get('vrfs',{}).items():
    if not isinstance(vdata.get(proto,None),Box):
      continue
    for intf in vdata[proto].get('interfaces',[]):
      yield intf
