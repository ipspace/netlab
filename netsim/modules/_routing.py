
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

from .. import common
from .. import addressing

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
        common.error(
          f'af attribute for {proto} on node {node.name} has to be a list or a dictionary',
          common.IncorrectValue,
          proto)
        return

      for proto_af in node[proto].af.keys():
        if not proto_af in ('ipv4','ipv6'):
          common.error(
            f'Routing protocol address family has to be ipv4 and/or ipv6: {proto} on {node.name}',
            common.IncorrectValue,
            proto)
  
  if not 'af' in node[proto]:           # No configured AF attribute, calculate it
    for af in ['ipv4','ipv6']:
      if af in node.loopback:           # Address family enabled on loopback?
        node[proto].af[af] = True       # ... we need it in the routing protocol
        continue

      for l in node.get('interfaces',[]): # Scan all interfaces
        if af in l:                       # Do we have AF enabled on any of them?
          node[proto].af[af] = True       # Found it - we need it the module
          continue

  for af in ['ipv4','ipv6']:              # Remove unused address families
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
      intf.proto.pop('network_type')
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

  return False

# IGP passive interfaces: stub link type or stub/passive role
#
def passive(intf: Box, proto: str) -> bool:
  if not 'passive' in intf[proto]:
    intf[proto].passive = intf.type == "stub" or intf.get('role',"") in ["stub","passive"]
  else:
    intf[proto].passive = bool(intf[proto].passive)
  return intf[proto].passive

# Create router ID if needed
#
def router_id(node: Box, proto: str, pools: Box) -> None:
  if 'router_id' in node.get(proto,{}):       # User-configured per-protocol router ID, get out of here
    try:
      node[proto].router_id = str(netaddr.IPAddress(node[proto].router_id).ipv4())
    except Exception as ex:
      common.error(
        f'{proto} router_id "{node[proto].router_id}" specified on node {node.name} is not an IPv4 address',
        common.IncorrectValue,
        proto)
    return

  if 'router_id' in node:                     # Node as configured router ID, copy it and get out
    try:
      node.router_id = str(netaddr.IPAddress(node.router_id).ipv4())
      node[proto].router_id = node.router_id
    except Exception as ex:
      common.error(
        f'router_id "{node.router_id}" specified on node {node.name} is not an IPv4 address',
        common.IncorrectValue,
        proto)
    return

  if 'ipv4' in node.get('loopback',{}):       # Do we have IPv4 address on the loopback? If so, use it as router ID
    node[proto].router_id = str(netaddr.IPNetwork(node.loopback.ipv4).ip)
    return

  if not pools.router_id:
    common.error(
      f'Cannot create a router ID for protocol {proto} on node {node.name}: router_id addressing pool is not defined',
      common.MissingValue,
      proto)
    return

  pfx = addressing.get(pools,['router_id'],node.id)
  if not pfx:
    common.error(
      f'Cannot create a router ID prefix from router_id pool for protocol {proto} on node {node.name}',
      common.IncorrectValue,
      proto)
    return

  if not pfx.get('ipv4',None):
    common.error(
      f'router_id pool did not return a usable IPv4 address to use as router ID for protocol {proto} on node {node.name}',
      common.IncorrectValue,
      proto)
    return

  node.router_id = str(netaddr.IPNetwork(pfx['ipv4']).ip)
  node[proto].router_id = node.router_id
