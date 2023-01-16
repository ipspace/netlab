#
# BGP transformation module
#
import typing

import re
from box import Box
import netaddr

from . import _Module,_routing
from .. import common
from .. import data
from ..data.validate import must_be_int,must_be_list,must_be_dict
from ..augment import devices

def check_bgp_parameters(node: Box) -> None:
  if not "bgp" in node:  # pragma: no cover (should have been tested and reported by the caller)
    return
  if not "as" in node.bgp:
    common.error(
      f"Node {node.name} has BGP enabled but no AS number specified",
      common.MissingValue,
      'bgp')
    return

  must_be_int(parent=node,key='bgp.as',path=f'nodes.{node.name}',min_value=1,max_value=65535,module='bgp')

  if "community" in node.bgp:
    bgp_comm = node.bgp.community
    if isinstance(bgp_comm,str):
      node.bgp.community = { 'ibgp' : [ bgp_comm ], 'ebgp': [ bgp_comm ]}
    elif isinstance(bgp_comm,list):
      node.bgp.community = { 'ibgp' : bgp_comm, 'ebgp': bgp_comm }
    elif not(isinstance(bgp_comm,dict)):
      common.error(
        f"bgp.community attribute in node {node.name} should be a string, a list, or a dictionary (found: {bgp_comm})",
        common.IncorrectType,
        'bgp')
      return

    for k in node.bgp.community.keys():
      if not k in ['ibgp','ebgp']:
        common.error("Invalid BGP community setting in node %s: %s" % (node.name,k))
      else:
        must_be_list(
          parent=node.bgp.community,
          path=f'nodes.{node.name}.bgp.community',
          key=k,
          valid_values=['standard','extended'],
          module='bgp')

BGP_VALID_AF: typing.Final[list] = ['ipv4','ipv6']
BGP_VALID_SESSION_TYPE: typing.Final[list] = ['ibgp','ebgp','localas_ibgp']

def validate_bgp_sessions(node: Box, sessions: Box, attribute: str) -> bool:
  OK = True
  for k in list(sessions.keys()):
    if not k in BGP_VALID_AF:
      common.error(
        f'Invalid address family in bgp.{attribute} in node {node.name}',
        common.IncorrectValue,
        'bgp')
      OK = False
    else:
      if must_be_list(
          parent=sessions,
          key=k,
          path=f'nodes.{node.name}.bgp.{attribute}',
          true_value=BGP_VALID_SESSION_TYPE,
          valid_values=BGP_VALID_SESSION_TYPE,
          module='bgp') is None:
        OK = False        

  return OK

"""
find_bgp_rr: find route reflectors in the specified autonomous system

Given an autonomous system and lab topology, return a list of node names that are route reflectors in that AS
"""
def find_bgp_rr(bgp_as: int, topology: Box) -> typing.List[Box]:
  return [ n 
    for n in topology.nodes.values() 
      if 'bgp' in n and n.bgp["as"] == bgp_as and n.bgp.get("rr",None) ]

"""
bgp_neighbor: Create BGP neighbor data structure

* n - neighbor node data
* intf - neighbor interface data (could be addressing prefix or whatever is in the interface neighbor list)
* ctype - session type (ibgp or ebgp)
* extra_data - anything else we might want to pass to the neighbor data structure
"""
def bgp_neighbor(n: Box, intf: Box, ctype: str, sessions: Box, extra_data: typing.Optional[dict] = None) -> typing.Optional[Box]:
  ngb = Box(extra_data or {},default_box=True,box_dots=True)
  ngb.name = n.name
  ngb["as"] = n.bgp.get("as")
  ngb["type"] = ctype
  af_count = 0
  for af in ["ipv4","ipv6"]:
    if ctype in sessions[af]:
      if af in intf:
        af_count = af_count + 1
        if "unnumbered" in ngb and ngb.unnumbered == True:
          ngb[af] = True
        elif isinstance(intf[af],bool):
          ngb[af] = intf[af]
        else:
          ngb[af] = str(netaddr.IPNetwork(intf[af]).ip)

  return ngb if af_count > 0 else None

"""
get_neighbor_rr: create extra data for bgp_neighbor function

Returns { rr: him } dict if the neighbor happens to be a RR. That dict will be merged with
the rest of the neighbor data
"""
def get_neighbor_rr(n: Box) -> typing.Optional[typing.Dict]:
  if "rr" in n.get("bgp"):
    return { "rr" : n.bgp.rr }

  return {}

"""
build_ibgp_sessions: create IBGP session data structure

* BGP route reflectors need IBGP session with all other nodes in the same AS
* Other nodes need IBGP sessions with all RRs in the same AS
"""
def build_ibgp_sessions(node: Box, sessions: Box, topology: Box) -> None:
  rrlist = find_bgp_rr(node.bgp.get("as"),topology)

  # If we don't have route reflectors, or if the current node is a route
  # reflector, we need BGP sessions to all other nodes in the same AS
  if not(rrlist) or node.bgp.get("rr",None):
    for name,n in topology.nodes.items():
      if "bgp" in n:
        if n.bgp.get("as") == node.bgp.get("as") and n.name != node.name:
          neighbor_data = bgp_neighbor(n,n.loopback,'ibgp',sessions,get_neighbor_rr(n))
          if not neighbor_data is None:
            node.bgp.neighbors.append(neighbor_data)

  #
  # The node is not a route reflector, and we have a non-empty RR list
  # We need BGP sessions with the route reflectors
  else:
    for n in rrlist:
      if n.name != node.name:
        neighbor_data = bgp_neighbor(n,n.loopback,'ibgp',sessions,get_neighbor_rr(n))
        if not neighbor_data is None:
          node.bgp.neighbors.append(neighbor_data)

"""
build_ebgp_sessions: create EBGP session data structure

* EBGP sessions are established whenever two nodes on the same link have different AS
"""
def build_ebgp_sessions(node: Box, sessions: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)

  #
  # Iterate over all links, find adjacent nodes
  # in different AS numbers, and create BGP neighbors
  for l in node.get("interfaces",[]):
    if 'bgp' in l and l.bgp is False:
      l.pop('bgp',None)                                               # Cleanup the flag
      continue                                                        # ... and skip interfaces with 'bgp: False'

    node_as =  node.bgp.get("as")                                     # Get our real AS number and the AS number of the peering session
    node_local_as = data.get_from_box(l,'bgp.local_as') or data.get_from_box(node,'bgp.local_as') or node_as

    af_list = [ af for af in ('ipv4','ipv6','unnumbered') if af in l ]
    if not af_list:                                                   # This interface has no usable address
      continue

    if node_as != node_local_as:
      if not features.bgp.local_as:
        common.error(
          text=f'{node.name} (device {node.device}) does not support BGP local AS (interface {l.name})',
          category=common.IncorrectValue,
          module='bgp')
        continue
      if l.get('vrf',None) and not features.bgp.vrf_local_as:
        common.error(
          text=f'{node.name} (device {node.device}) does not support BGP local AS for EBGP sessions in VRF {l.vrf}',
          category=common.IncorrectValue,
          module='bgp')
        continue

    for ngb_ifdata in l.get("neighbors",[]):
      af_list = [ af for af in ('ipv4','ipv6','unnumbered') if af in ngb_ifdata ]
      if not af_list:                                                 # Neighbor has no usable address
        continue
      #
      # Get neighbor node data and its true or interface-local AS
      #
      ngb_name = ngb_ifdata.node
      neighbor = topology.nodes[ngb_name]
      neighbor_real_as = data.get_from_box(neighbor,'bgp.as')
      neighbor_local_as = data.get_from_box(ngb_ifdata,'bgp.local_as') or data.get_from_box(neighbor,'bgp.local_as') or neighbor_real_as

      if not neighbor_local_as:                                       # Neighbor has no usable BGP AS number, move on
        continue

      if node_as == neighbor_real_as and node_local_as == neighbor_local_as:
        continue                                                      # Routers in the same AS + no local-as trickery => nothing to do here

      extra_data = Box({})
      extra_data.ifindex = l.ifindex

      # Figure out whether both neighbors have IPv6 LLA and/or unnumbered IPv4 interfaces
      #
      ipv6_lla = l.get('ipv6',None) is True and ngb_ifdata.get('ipv6',None) is True
      ipv6_num = isinstance(l.get('ipv6',None),str) and isinstance(ngb_ifdata.get('ipv6',None),str)
      rfc8950  = l.get('unnumbered',None) is True and ngb_ifdata.get('unnumbered',None) is True
      ipv4_unnum = l.get('ipv4',None) is True and ngb_ifdata.get('ipv4',None) is True
#      print(f'EBGP node {node.name} neighbor {ngb_name} lla {ipv6_lla} v6num {ipv6_num} v4unnum {ipv4_unnum} rfc8950 {unnumbered}')
      if ipv4_unnum and not ipv6_num:                                 # Unnumbered IPv4 w/o IPv6 ==> IPv6 LLA + RFC 8950 IPv4 AF
        rfc8950 = True

#      print(f'... unnumbered {unnumbered}')
      if ipv6_lla or rfc8950:
        extra_data.local_if = l.ifname                                # Set local_if to indicate IPv6 LLA EBGP session
        if not features.bgp.ipv6_lla:                                 # IPv6_LLA feature flag has to be set even for IPv4 unnumbered EBGP
          common.error(
            text=f'{node.name} (device {node.device}) does not support EBGP sessions over auto-generated IPv6 LLA (interface {l.name})',
            category=common.IncorrectValue,
            module='bgp')
          continue

      if rfc8950:
        extra_data.ipv4_rfc8950 = True                                # Set unnumbered indicate RFC 8950 IPv4 AF
        if not 'ipv6' in l:                                           # ... and enable IPv6 on the interface in case a device needs an
          l.ipv6 = True                                               # ... explicit configuration of IPv6 LLA
        if not features.bgp.rfc8950:
          common.error(
            text=f'{node.name} (device {node.device}) does not support IPv4 RFC 8950-style AF over IPv6 LLA EBGP sessions (interface {l.name})',
            category=common.IncorrectValue,
            module='bgp')
          continue

      for k in ('local_as','replace_global_as'):
        local_as_data = data.get_from_box(l,f'bgp.{k}') or data.get_from_box(node,f'bgp.{k}')
        if not local_as_data is None:
          extra_data[k] = local_as_data

      session_type = 'localas_ibgp' if neighbor_local_as == node_local_as else 'ebgp'
      if session_type == 'localas_ibgp':
        if not features.bgp.local_as_ibgp:
          common.error(
            text=f'You cannot use BGP local-as to create an IBGP session with {ngb_name} on {node.name} (device {node.device})',
            category=common.IncorrectValue,
            module='bgp')
          continue

      ebgp_data = bgp_neighbor(neighbor,ngb_ifdata,session_type,sessions,extra_data)
      if not ebgp_data is None:
        ebgp_data['as'] = neighbor_local_as
        if 'vrf' in l:        # VRF neighbor
          if not node.vrfs[l.vrf].bgp is False:
            if not node.vrfs[l.vrf].bgp.neighbors:
              node.vrfs[l.vrf].bgp.neighbors = []
            node.vrfs[l.vrf].bgp.neighbors.append(ebgp_data)
        else:                 # Global neighbor
          node.bgp.neighbors.append(ebgp_data)

"""
activate_bgp_default_af -- activate default AF on IPv4 and/or IPv6 transport sessions

Based on transport session(s) with a BGP neighbor, local BGP AF, and BGP AF configuration
parameters, set neighbor.activate.AF flags
"""

def activate_bgp_default_af(node: Box, activate: Box, topology: Box) -> None:
  for ngb in node.bgp.neighbors:
    for af in ('ipv4','ipv6'):
      if af in ngb:
        ngb.activate[af] = node.bgp.get(af) and af in activate and ngb.type in activate[af]

"""
Build BGP route reflector clusters

Iterate over all ASNs in the lab, and for route reflectors that don't have rr_cluster_id
defined, find an AS-wide cluster ID: the lowest BGP router ID of all route reflectors
(members of rr_list) that don't have rr_cluster_id set (because those obviously want to be left alone)
"""
def build_bgp_rr_clusters(topology: Box) -> None:
  # Build a list of autonomous systems in the lab
  as_list = set( n.bgp['as'] for n in topology.nodes.values() if 'bgp' in n and 'as' in n.bgp )

  for asn in as_list:
    rrlist = find_bgp_rr(asn,topology)
    if not rrlist:                        # No BGP route reflectors in this ASN
      continue

    # Build a list of RR cluster candidates: router IDs of route reflectors that don't
    # have an explicit rr_cluster_id
    #
    # The shared cluster ID will be the minimum value from that list
    #
    rr_cluster_candidates = [n.bgp.router_id for n in rrlist if not 'rr_cluster_id' in n.bgp]
    rr_cluster_id = None
    if rr_cluster_candidates:
      rr_cluster_id = min(rr_cluster_candidates)

    # Now iterate over the route reflectors and either set the shared cluster ID
    # or validate that the static cluster ID is an IPv4 address
    #
    for n in rrlist:
      if not 'rr_cluster_id' in n.bgp:
        n.bgp.rr_cluster_id = rr_cluster_id or n.bgp.router_id
      elif n.bgp.rr_cluster_id:
        try:
          n.bgp.rr_cluster_id = str(netaddr.IPAddress(n.bgp.rr_cluster_id).ipv4())
        except Exception as ex:
          common.error(
            f'BGP cluster ID {n.bgp.rr_cluster_id} configured on node {n.name} cannot be converted into an IPv4 address',
            common.IncorrectValue,
            'bgp')

"""
build_bgp_sessions: create BGP session data structure

* Create an empty list of BGP neighbors
* Create IBGP sessions
* Create EBGP sessions
* Set BGP AF flags
"""

BGP_DEFAULT_SESSIONS: typing.Final[dict] = {
  'ipv4': [ 'ibgp', 'ebgp', 'localas_ibgp' ],
  'ipv6': [ 'ibgp', 'ebgp', 'localas_ibgp' ]
}

def build_bgp_sessions(node: Box, topology: Box) -> None:
  if not data.get_from_box(node,'bgp.as'):                        # Sanity check: do we have usable AS number
    common.fatal(f'build_bgp_sessions: node {node.name} has no usable BGP AS number, how did we get here???')
    return                                                        # ... not really, get out of here

  node.bgp.neighbors = []
  bgp_sessions = node.bgp.get('sessions') or Box(BGP_DEFAULT_SESSIONS)
  if not validate_bgp_sessions(node,bgp_sessions,'sessions'):
    return

  build_ibgp_sessions(node,bgp_sessions,topology)
  build_ebgp_sessions(node,bgp_sessions,topology)

  # Calculate BGP address families
  #
  for af in ['ipv4','ipv6']:
    for n in node.bgp.neighbors:
      if af in n:
        node.bgp[af] = True
        break

  # Activate default BGP address families
  features = devices.get_device_features(node,topology.defaults)
  if 'activate' in node.bgp:
    if not features.bgp.activate_af:
      common.error(
        f'node {node.name} (device {node.device}) does not support configurable activation of default BGP address families',
        common.IncorrectValue,
        'bgp')
      return

  activate = node.bgp.get('activate') or Box(BGP_DEFAULT_SESSIONS)
  if not validate_bgp_sessions(node,activate,'activate'):
    return

  activate_bgp_default_af(node,activate,topology)

"""
bgp_set_advertise: set bgp.advertise flag on stub links and on loopback interfaces
"""
def bgp_set_advertise(node: Box, topology: Box) -> None:
  stub_roles = data.get_global_parameter(topology,"bgp.advertise_roles") or []

  for l in node.get("interfaces",[]):
    if "bgp" in l:
      if l.bgp is False:                    # Skip interfaces on which we don't want to run BGP
        continue
      if "advertise" in l.bgp:              # Skip interfaces that already have the 'advertise' flag
        continue
    if l.get("type",None) in stub_roles or l.get("role",None) in stub_roles:
      l.bgp.advertise = True                # ... otherwise figure out whether to advertise the subnet
      continue
    if l.get('type',None) == 'loopback' and node.bgp.advertise_loopback:
      l.bgp.advertise = True                # ... also advertise loopback prefixes if bgp.advertise_loopback is set

"""
process_as_list:
  If the global BGP parameters have as_list attribute, set node AS numbers and node
  RR flags accordingly
"""
def process_as_list(topology: Box) -> None:
  if not data.get_from_box(topology,'bgp.as_list'):         # Do we have global bgp.as_list setting?
    return                                                  # ... nope, no work for me ;)) 

  try:
    must_be_dict(topology.bgp,'as_list','bgp',create_empty=False,module='bgp',abort=True)
  except Exception as ex:
    return

  node_data = Box({},default_box=True,box_dots=True)
  node_list = list(topology.nodes.keys())
  for asn,as_data in topology.bgp.as_list.items():
    if not isinstance(as_data,Box):
      common.error(
        f"Invalid value in bgp.as_list for ASN {asn}\n" + \
        f"... Each ASN in a BGP as_list must be a dictionary with (at least) members key:\n"+
        f"... Found: {as_data}",
        common.IncorrectValue,
        'bgp')
      continue

    must_be_list(as_data,'members',f'bgp.as_list.{asn}',create_empty=False,module='bgp',valid_values=node_list)
    must_be_list(as_data,'rr',f'bgp.as_list.{asn}',create_empty=False,module='bgp',valid_values=node_list)
    if not as_data.members:
      common.error(
        f"BGP as_list for ASN {asn} does not have a valid list of members",
        common.IncorrectValue,
        'bgp')
      continue

    for n in as_data.members:
      if 'as' in node_data[n]:
        common.error(
          f"BGP module supports at most 1 AS per node; {n} is already member of {node_data[n]['as']} and cannot also be part of {asn}",
          common.IncorrectValue)
        continue
      node_data[n]["as"] = asn

    for n in as_data.get('rr',{}):
      if node_data[n]["as"] != asn:
        common.error(
          "Node %s is specified as route reflector in AS %s but is not in member list" % (n,asn),
          common.IncorrectValue)
        continue
      node_data[n].rr = True

  for name,node in topology.nodes.items():
    if name in node_data:
      node_as = node.bgp.get("as",None)
      if node_as and node_as != node_data[name]["as"]:
        common.error(
          "Node %s has AS %s but is also in member list of AS %s" % (node.name,node_as,node_data[node.name]["as"]),
          common.IncorrectValue)
        continue

      node.bgp = node_data[name] + node.bgp

class BGP(_Module):

  """
  Module pre-default:

  * process AS list
  * create automatic BGP groups
  """
  def module_pre_default(self, topology: Box) -> None:
    pass

  """
  Node pre-transform: set bgp.rr node attribute to _true_ if the node name is in the
  global bgp.rr attribute. Also, delete the global bgp.rr attribute so it's not propagated
  down to nodes
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if "rr_list" in topology.get("bgp",{}):
      if node.name in topology.bgp.rr_list:
        node.bgp.rr = True

    check_bgp_parameters(node)

  """
  Link pre-transform: Set link role based on BGP nodes attached to the link.

  If the nodes belong to at least two autonomous systems, and the ebgp_role
  variable is set, set the link role to ebgp_role
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    ebgp_role = topology.bgp.get("ebgp_role",None) or topology.defaults.bgp.get("ebgp_role",None)
    if not ebgp_role:
      return

    as_set = {}
    for ifdata in link.get('interfaces',[]):
      n = ifdata.node
      if "bgp" in topology.nodes[n]:
        node_as = topology.nodes[n].bgp.get("as")
        if node_as:
          as_set[node_as] = True

    if len(as_set) > 1 and not link.get("role"):
      link.role = ebgp_role

  #
  # Have to set BGP router IDs and cluster IDs before going into node_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'bgp' in n:
        _routing.router_id(n,'bgp',topology.pools)

    build_bgp_rr_clusters(topology)

  #
  # Execute the rest of node post-transform code, including setting up the BGP session table
  #
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not "bgp" in node:   # pragma: no cover (this should have been caught in check_bgp_parameters)
      common.fatal(f"Internal error: node {node.name} has BGP module enabled but no BGP parameters","bgp")
      return
    build_bgp_sessions(node,topology)
    bgp_set_advertise(node,topology)
    _routing.remove_vrf_routing_blocks(node,'bgp')
