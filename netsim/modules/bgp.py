#
# BGP transformation module
#
import typing

import re
from box import Box
import netaddr

from . import _Module,_routing
from .. import common
from ..augment.links import IFATTR

def check_bgp_parameters(node: Box) -> None:
  if not "bgp" in node:  # pragma: no cover (should have been tested and reported by the caller)
    return
  if not "as" in node.bgp or not isinstance(node.bgp.get('as',{}),int):
    common.error("Node %s has BGP enabled but no AS number specified" % node.name)

  if "community" in node.bgp:
    bgp_comm = node.bgp.community
    if isinstance(bgp_comm,str):
      node.bgp.community = { 'ibgp' : [ bgp_comm ], 'ebgp': [ bgp_comm ]}
    elif isinstance(bgp_comm,list):
      node.bgp.community = { 'ibgp' : bgp_comm, 'ebgp': bgp_comm }
    elif not(isinstance(bgp_comm,dict)):
      common.error("bgp.community attribute in node %s should be a string, a list, or a dictionary (%s)" % (node.name,str(bgp_comm)))
      return

    for k in node.bgp.community.keys():
      if not k in ['ibgp','ebgp']:
        common.error("Invalid BGP community setting in node %s: %s" % (node.name,k))
      if isinstance(node.bgp.community[k],str):
        node.bgp.community[k] = [ node.bgp.community[k] ]
      for v in node.bgp.community[k]:
        if not v in ['standard','extended']:
          common.error("Invalid BGP community propagation setting for %s sessions in node %s: %s" % (k,node.name,v))

def find_bgp_rr(bgp_as: int, topology: Box) -> typing.List[Box]:
  return [ n 
    for n in topology.nodes.values() 
      if 'bgp' in n and n.bgp["as"] == bgp_as and n.bgp.get("rr",None) ]

def bgp_neighbor(n: Box, intf: Box, ctype: str, extra_data: typing.Optional[dict] = None) -> Box:
  ngb = Box(extra_data or {},default_box=True,box_dots=True)
  ngb.name = n.name
  ngb["as"] = n.bgp.get("as")
  ngb["type"] = ctype
  for af in ["ipv4","ipv6"]:
    if af in intf:
      if "unnumbered" in ngb and ngb.unnumbered == True:
        ngb[af] = True
      else:
        ngb[af] = str(netaddr.IPNetwork(intf[af]).ip)
  return ngb

def get_neighbor_rr(n: Box) -> typing.Optional[typing.Dict]:
  if "rr" in n.get("bgp"):
    return { "rr" : n.bgp.rr }

  return {}

class BGP(_Module):

  '''
  process_as_list:
    If the global BGP parameters have as_list attribute, set node AS numbers and node
    RR flags accordingly
  '''
  def process_as_list(self, topology: Box) -> None:
    if not 'bgp' in topology:                            # Do we have global BGP settings?
      return

    if not 'as_list' in topology.bgp:                    # Do we have global AS list?
      return

    if not isinstance(topology.bgp.as_list,dict):
      common.error(
        "bgp.as_list should be a dictionary of AS parameters",
        common.IncorrectValue)
      return

    node_data = Box({},default_box=True,box_dots=True)
    for asn,data in topology.bgp.as_list.items():
      if not isinstance(data,Box):
        common.error(
          "Invalid value in bgp.as_list for ASN %s: " % asn + \
          "\n... Each ASN in a BGP as_list must be a dictionary with (at least) members key:"+
          "\n... Found: %s" % data,
          common.IncorrectValue)
        continue

      if not 'members' in data:
        common.error(
          "BGP as_list for ASN %s does not have a member attribute" % asn,
          common.IncorrectValue)
        continue

      common.must_be_list(data,'members',f'bgp.as_list.{asn}')
      for n in data.members:
        if not n in topology.nodes:
          common.error(
            "Invalid node name %s in member list of BGP AS %s" % (n,asn),
            common.IncorrectValue)
          continue
        elif 'as' in node_data[n]:
          common.error(
            f"BGP module supports at most 1 AS per node; {n} is already member of {node_data[n]['as']} and cannot also be part of {asn}",
            common.IncorrectValue)
          continue
        node_data[n]["as"] = asn

      for n in data.get('rr',{}):
        if not n in topology.nodes:
          common.error(
            "Invalid node name %s in route reflector list of BGP AS %s" % (n,asn),
            common.IncorrectValue)
          continue
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

  '''
  bgp_build_group: create automatic groups based on BGP AS numbers
  '''
  def build_bgp_groups(self, topology: Box) -> None:
    for gname,gdata in topology.groups.items():
      if re.match('as\\d+$',gname):
        if gdata.get('members',None):
          common.error('BGP AS groups should not have static members %s' % gname)

    for name,node in topology.nodes.items():
      if 'bgp' in node and 'as' in node.bgp:
        grpname = "as%s" % node.bgp["as"]
        if not grpname in topology.groups:
          topology.groups[grpname] = { 'members': [] }

        if not 'members' in topology.groups[grpname]:   # pragma: no cover (members list is created in group processing)
          topology.groups[grpname].members = []

        topology.groups[grpname].members.append(name)

  """
  Module pre-default:

  * process AS list
  * create automatic BGP groups
  """
  def module_pre_default(self, topology: Box) -> None:
    self.process_as_list(topology)
    self.build_bgp_groups(topology)

  """
  Node pre-transform: set bgp.rr node attribute to _true_ if the node name is in the
  global bgp.rr attribute. Also, delete the global bgp.rr attribute so it's not propagated
  down to nodes
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if "rr_list" in topology.get("bgp",{}):
      if node.name in topology.bgp.rr_list:
        node.bgp.rr = True

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
    for ifdata in link.get(IFATTR,[]):
      n = ifdata.node
      if "bgp" in topology.nodes[n]:
        node_as = topology.nodes[n].bgp.get("as")
        if node_as:
          as_set[node_as] = True

    if len(as_set) > 1 and not link.get("role"):
      link.role = ebgp_role

  """
  build_bgp_sessions: create BGP session data structure

  * BGP route reflectors need IBGP session with all other nodes in the same AS
  * Other nodes need IBGP sessions with all RRs in the same AS
  * EBGP sessions are established whenever two nodes on the same link have different AS
  * Links matching 'advertise_roles' get 'advertise' attribute set
  """
  def build_bgp_sessions(self, node: Box, topology: Box) -> None:
    rrlist = find_bgp_rr(node.bgp.get("as"),topology)
    node.bgp.neighbors = []

    # If we don't have route reflectors, or if the current node is a route
    # reflector, we need BGP sessions to all other nodes in the same AS
    if not(rrlist) or node.bgp.get("rr",None):
      for name,n in topology.nodes.items():
        if "bgp" in n:
          if n.bgp.get("as") == node.bgp.get("as") and n.name != node.name:
            node.bgp.neighbors.append(bgp_neighbor(n,n.loopback,'ibgp',get_neighbor_rr(n)))

    #
    # The node is not a route reflector, and we have a non-empty RR list
    # We need BGP sessions with the route reflectors
    else:
      for n in rrlist:
        if n.name != node.name:
          node.bgp.neighbors.append(bgp_neighbor(n,n.loopback,'ibgp',get_neighbor_rr(n)))

    #
    # EBGP sessions - iterate over all links, find adjacent nodes
    # in different AS numbers, and create BGP neighbors
    for l in node.get("interfaces",[]):
      for ngb_ifdata in l.get("neighbors",[]):
        ngb_name = ngb_ifdata.node
        neighbor = topology.nodes[ngb_name]
        if not "bgp" in neighbor:
          continue
        if neighbor.bgp.get("as") and neighbor.bgp.get("as") != node.bgp.get("as"):
          extra_data = Box({})
          extra_data.ifindex = l.ifindex
          if "unnumbered" in l:
            extra_data.unnumbered = True
            extra_data.local_if = l.ifname
          node.bgp.neighbors.append(bgp_neighbor(neighbor,ngb_ifdata,'ebgp',extra_data))

    # Calculate BGP address families
    #
    for af in ['ipv4','ipv6']:
      for n in node.bgp.neighbors:
        if af in n:
          node.bgp[af] = True
          break

  '''
  bgp_set_advertise: set bgp.advertise flag on stub links
  '''
  def bgp_set_advertise(self, node: Box, topology: Box) -> None:
    stub_roles = topology.defaults.bgp.get("advertise_roles",None)
    if 'advertise_roles' in topology.bgp:
      stub_roles = topology.bgp.get("advertise_roles",None)
    if stub_roles:
      for l in node.get("interfaces",[]):
        if "bgp" in l:
          if "advertise" in l.bgp:
            continue
        if l.get("type",None) in stub_roles or l.get("role",None) in stub_roles:
          if not 'bgp' in l:
            l.bgp = {}
          l.bgp.advertise = True

  #
  # Have to set BGP router IDs and cluster IDs before going into node_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'bgp' in n:
        _routing.router_id(n,'bgp',topology.pools)

    # Build a list of autonomous systems in the lab
    as_list = set( n.bgp['as'] for n in topology.nodes.values() if 'bgp' in n and 'as' in n.bgp )

    # Iterate over all ASNs in the lab, and for route reflectors that don't have rr_cluster_id
    # defined, find an AS-wide cluster ID: the lowest BGP router ID of all route reflectors
    # (members of rr_list) that don't have rr_cluster_id set (because those obviously want to be left alone)
    #
    for asn in as_list:
      rrlist = find_bgp_rr(asn,topology)
      if rrlist:
        rr_cluster_candidates = [n.bgp.router_id for n in rrlist if not 'rr_cluster_id' in n.bgp]
        rr_cluster_id = None
        if rr_cluster_candidates:
          rr_cluster_id = min(rr_cluster_candidates)
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

  #
  # Execute the rest of node post-transform code, including setting up the BGP session table
  #
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not "bgp" in node:   # pragma: no cover (this should have been caught in check_bgp_parameters)
      common.fatal(f"Internal error: node {node.name} has BGP module enabled but no BGP parameters","bgp")
      return
    check_bgp_parameters(node)
    self.build_bgp_sessions(node,topology)
    self.bgp_set_advertise(node,topology)
