#
# BGP transformation module
#
import typing

import re
from box import Box
import netaddr

from . import _Module
from .. import common

def check_bgp_parameters(node: Box) -> None:
  if not "bgp" in node:
    return
  if not "as" in node.bgp:
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
  rrlist = []
  for n in topology.nodes:
    if not "bgp" in n:
      continue
    if n.bgp["as"] == bgp_as and n.bgp.get("rr",None):
      rrlist.append(n)
  return rrlist

def bgp_neighbor(n: Box, intf: Box, ctype: str, extra_data: typing.Optional[dict] = None) -> Box:
  ngb = Box(extra_data or {},default_box=True,box_dots=True)
  ngb.name = n.name
  ngb["as"] = n.bgp.get("as")
  ngb["type"] = ctype
  for af in ['ipv4','ipv6']:
    if af in intf:
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

      for n in data.members:
        if not n in topology.nodes_map:
          common.error(
            "Invalid node name %s in member list of BGP AS %s" % (n,asn),
            common.IncorrectValue)
          continue
        node_data[n]["as"] = asn

      for n in data.get('rr',{}):
        if not n in topology.nodes_map:
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

    for node in topology.nodes:
      if node.name in node_data:
        node_as = node.bgp.get("as",None)
        if node_as and node_as != node_data[node.name]["as"]:
          common.error(
            "Node %s has AS %s but is also in member list of AS %s" % (node.name,node_as,node_data[node.name]["as"]),
            common.IncorrectValue)
          continue

        node.bgp = node_data[node.name] + node.bgp

  '''
  bgp_build_group: create automatic groups based on BGP AS numbers
  '''
  def build_bgp_groups(self, topology: Box) -> None:
    for gname,gdata in topology.groups.items():
      if re.match('as\\d+$',gname):
        if 'members' in gdata:
          common.error('BGP AS groups should not have static members %s' % gname)

    for node in topology.nodes:
      if 'bgp' in node and 'as' in node.bgp:
        grpname = "as%s" % node.bgp["as"]
        if not grpname in topology.groups:
          topology.groups[grpname] = { 'members': [] }

        if not 'members' in topology.groups[grpname]:
          topology.groups[grpname].members = []

        topology.groups[grpname].members.append(node.name)

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
    for n in link.keys():
      if n in topology.nodes_map:
        if "bgp" in topology.nodes_map[n]:
          node_as = topology.nodes_map[n].bgp.get("as")
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
      for n in topology.nodes:
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
    for l in node.get("links",[]):
      for ngb_name,ngb_ifdata in l.get("neighbors",{}).items():
        neighbor = topology.nodes_map[ngb_name]
        if not "bgp" in neighbor:
          continue
        if neighbor.bgp.get("as") and neighbor.bgp.get("as") != node.bgp.get("as"):
          extra_data = Box({})
          extra_data.ifindex = l.ifindex
          if "unnumbered" in l:
            extra_data.unnumbered = True
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
      for l in node.get("links",[]):
        if "bgp" in l:
          if "advertise" in l.bgp:
            continue
        if l.get("type",None) in stub_roles or l.get("role",None) in stub_roles:
          if not 'bgp' in l:
            l.bgp = {}
          l.bgp.advertise = True

  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not "bgp" in node:
      common.error("Node %s has BGP module enabled but no BGP parameters" % node.name)
    check_bgp_parameters(node)
    self.build_bgp_sessions(node,topology)
    self.bgp_set_advertise(node,topology)
