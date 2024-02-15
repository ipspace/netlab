
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
from ..augment import addressing
from .. import data

# Build routing protocol address families
#
# * If the address families are not set, calculate them based on interface address families
# * Otherwise parse and validate the AF attribute
#
def routing_af(node: Box, proto: str) -> None:
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

  for af in ['ipv4','ipv6']:                          # Remove unused address families
    if not node[proto].af.get(af,False):
      node[proto].af.pop(af,False)

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

# Figure out whether an IGP interface should be passive
#
# * The proto.passive flag is set
# * The link role is 'passive' (set manually) or the link is a stub link (single node attached to it)
# * The link is a stub link (so it has at most one non-host attached)
#   and other devices on the link are not running the same protocol (so no daemons)
#
def passive(intf: Box, proto: str, topology: Box) -> None:
  if 'passive' in intf[proto]:                              # Explicit 'passive' flag
    intf[proto].passive = bool(intf[proto].passive)         # ... turn it into bool (just in case)
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

  if 'router_id' in node:                     # Node as configured router ID, copy it and get out
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

  if not pools.router_id:
    log.error(
      f'Cannot create a router ID for protocol {proto} on node {node.name}: router_id addressing pool is not defined',
      log.MissingValue,
      proto)
    return

  pfx = addressing.get(pools,['router_id'],node.id)
  if not pfx:
    log.error(
      f'Cannot create a router ID prefix from router_id pool for protocol {proto} on node {node.name}',
      log.IncorrectValue,
      proto)
    return

  if not pfx.get('ipv4',None):
    log.error(
      f'router_id pool did not return a usable IPv4 address to use as router ID for protocol {proto} on node {node.name}',
      log.IncorrectValue,
      proto)
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
def remove_unused_igp(node: Box, proto: str) -> None:
  if not any(proto in ifdata for ifdata in node.interfaces):                # Is protocol configured on any non-loopback interface?
    node.pop(proto,None)                                                    # ... no, remove protocol data from node

  if proto in node and 'af' in node[proto] and node[proto].af:              # Is at least one global AF active for the protocol?
    return                                                                  # ... OK, we're good

  for vdata in node.get('vrfs',{}).values():                                # Is protocol active in at least one VRF?
    if proto in vdata:
      return                                                                # ... OK, we're good

  node.module = [ m for m in node.module if m != proto ]                    # Makes no sense to keep it, remove the config module

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
get_remote_cp_endpoint: find the remote control-plane endpoint

Return loopback interface or the first physical interface
"""
def get_remote_cp_endpoint(n: Box) -> Box:
  if 'loopback' in n and n.get('role') != 'host':           # The node has loopback and is not a host
    return n.loopback                                       # ... can't use loopback if the node has no routing

  if n.interfaces:                                          # Hope the node has at least one usable interface
    return n.interfaces[0]                                  # ... if it does, return that

  return data.get_empty_box()                               # Otherwise return an empty box
