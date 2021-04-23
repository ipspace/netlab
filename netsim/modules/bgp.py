#
# BGP transformation module
#

from box import Box
import netaddr

from . import Module
from .. import common

def check_bgp_parameters(node):
  if "bgp" in node:
    if not "as" in node.bgp:
      common.error("Node %s has BGP enabled but no AS number specified" % node.name)

def find_bgp_rr(bgp_as,topology):
  rrlist = []
  for n in topology.nodes:
    if not "bgp" in n:
      continue
    if n.bgp["as"] == bgp_as and n.bgp.get("rr",None):
      rrlist.append(n)
  return rrlist

def bgp_neighbor(n,intf,ctype,extra_data={}):
  ngb = Box(extra_data,default_box=True,box_dots=True)
  ngb.name = n.name
  ngb["as"] = n.bgp.get("as")
  ngb["type"] = ctype
  for af in ['ipv4','ipv6']:
    if af in intf:
      ngb[af] = str(netaddr.IPNetwork(intf[af]).ip)
  return ngb

def get_neighbor_rr(n):
  if "rr" in n.get("bgp"):
    return { "rr" : n.bgp.rr }

  return {}

class BGP(Module):

  """
  Module pre-default:

  * If the global BGP parameters have as_list attribute, set node AS numbers and node
    RR flags accordingly

  We could implement this one as node pre_default, but then we'd have to repeatedly
  scan the AS_list
  """
  def module_pre_default(self,topology):
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
      for n in data.get('members',{}):
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

  """
  Node pre-transform: set bgp.rr node attribute to _true_ if the node name is in the
  global bgp.rr attribute. Also, delete the global bgp.rr attribute so it's not propagated
  down to nodes
  """
  def node_pre_transform(self,node,topology):
    if "rr_list" in topology.get("bgp",{}):
      if node.name in topology.bgp.rr_list:
        node.bgp.rr = True

  """
  Link pre-transform: Set link role based on BGP nodes attached to the link.

  If the nodes belong to at least two autonomous systems, and the ebgp_role
  variable is set, set the link role to ebgp_role
  """
  def link_pre_transform(self,link,topology):
    ebgp_role = topology.bgp.get("ebgp_role",None) or topology.defaults.bgp.get("ebgp_role",None)
    if not ebgp_role:
      return

    as_set = {}
    for n in link.keys():
      if n in topology.nodes_map:
        if "bgp" in topology.nodes_map[n]:
          node_as = topology.nodes_map[n].bgp.get("as")
        as_set[node_as] = True

    if len(as_set) > 1 and not link.get("role"):
      link.role = ebgp_role

  """
  Node post-transform: build BGP sessions

  * BGP route reflectors need IBGP session with all other nodes in the same AS
  * Other nodes need IBGP sessions with all RRs in the same AS
  * EBGP sessions are established whenever two nodes on the same link have different AS
  * Links matching 'advertise_roles' get 'advertise' attribute set
  """
  def node_post_transform(self,node,topology):
    if not "bgp" in node:
      common.error("Node %s has BGP module enabled but no BGP parameters" % node.name)
    check_bgp_parameters(node)
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
          if "unnumbered" in l:
            extra_data.unnumbered = True
            extra_data.ifindex = l.ifindex
          node.bgp.neighbors.append(bgp_neighbor(neighbor,ngb_ifdata,'ebgp',extra_data))

    # Set bgp.advertise flag on stub links
    #
    stub_roles = topology.bgp.get("advertise_roles",None) or topology.defaults.bgp.get("advertise_roles",None)
    if stub_roles:
      for l in node.get("links",[]):
        if "bgp" in l:
          if "advertise" in l.bgp:
            continue
        if l.get("type",None) in stub_roles or l.get("role",None) in stub_roles:
          l.bgp.advertise = True

