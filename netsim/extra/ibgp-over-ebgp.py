#
# BGP neighbors transformation module to support multiple AS per node
#
# WARNING: There be dragons here...
# The core bgp module only supports a single AS per node, as that is the more
# common and simple way to operate BGP. Most vendors/devices can support
# multiple AS, for example in a topology that uses iBGP for an EVPN overlay and
# eBGP for the underlay. This module reorganizes bgp.neighbors to support such
# topologies
#
# Changes:
# * bgp.neighbors of type 'ebgp' get a local_as attribute
#
import typing, netaddr
from box import Box

"""
Similar to Module pre-default:
* process AS list
* build BGP groups with multi-AS support
"""
def init(topology: Box) -> None:
    # Temporary attribute, removed at end
    topology.defaults.bgp.attributes.node.append('ibgp_over_ebgp')

    process_as_list(topology)
    # build_bgp_groups(topology)

# The core 'bgp' module does not support multiple AS per node;
# recalculate our own configs under bgp.ibgp_over_ebgp
def process_as_list(topology: Box) -> None:
    node_data = Box({},default_box=True,box_dots=True)
    ibgp_as = topology.bgp['as']
    for asn,data in topology.bgp.as_list.items():
      for n in data.members:
        node_data[n]["as"] += { asn: True } # Support multiple AS
      for n in data.get('rr',{}):
        node_data[n].rr = asn # RR role is for a particular AS
      if 'ibgp' in data and data.ibgp:
        ibgp_as = asn

    for name,node in topology.nodes.items():
      if name in node_data:
        if ibgp_as!=0:
          node.bgp.ibgp_over_ebgp.ibgp_as = ibgp_as
        node.bgp.ibgp_over_ebgp = node_data[name] + node.bgp.ibgp_over_ebgp

'''
bgp_build_group: create automatic groups based on BGP AS numbers
'''
def build_bgp_groups(topology: Box) -> None:
    for name,node in topology.nodes.items():
      if 'bgp' in node and 'as' in node.bgp.ibgp_over_ebgp: # multi-AS
        for asn in node.bgp.ibgp_over_ebgp['as'].keys():
          grpname = f"as{asn}" # Dont create conflicts with bgp module
          if not grpname in topology.groups:
            topology.groups[grpname] = { 'members': [] }

          if not 'members' in topology.groups[grpname]:   # pragma: no cover (members list is created in group processing)
            topology.groups[grpname].members = []

          if name not in topology.groups[grpname].members:
            print( f"ibgp-over-ebgp: Adding node {name} to AS group {grpname}" )
            topology.groups[grpname].members.append(name)

def find_bgp_rr(bgp_as: int, topology: Box) -> typing.List[Box]:
  rrlist = []
  for name,n in topology.nodes.items():
    if ("bgp" in n and bgp_as in n.bgp.ibgp_over_ebgp["as"]):
      if n.bgp.ibgp_over_ebgp.get("rr",0) == bgp_as:
        rrlist.append(n)
  return rrlist

def bgp_neighbor(n: Box, type: str, asn: int, intf: Box, extra_data: typing.Optional[dict] = None) -> Box:
  ngb = Box(extra_data or {},default_box=True,box_dots=True)
  ngb.name = n.name
  ngb.type = type
  ngb["peer_as"] = ngb["as"] = asn  # 'as' for backwards compatibility
  for af in ["ipv4","ipv6"]:
    if af in intf:
      if "unnumbered" in ngb and ngb.unnumbered == True:
        ngb[af] = True
      else:
        ngb[af] = str(netaddr.IPNetwork(intf[af]).ip)
  return ngb


"""
build_bgp_sessions: create BGP session data structure, with multi-AS support
* BGP route reflectors need IBGP session with all other nodes in the same AS
* Other nodes need IBGP sessions with all RRs in the same AS
* EBGP sessions are established whenever two nodes on the same link have different AS
* Links matching 'advertise_roles' get 'advertise' attribute set
"""
def build_bgp_sessions(node: Box, topology: Box) -> None:
    for asn in node.bgp.ibgp_over_ebgp['as'].keys():
      rrlist = find_bgp_rr(asn,topology)

      # If we don't have route reflectors, or if the current node is a route
      # reflector, we need iBGP sessions to all other nodes in the same AS
      node_is_rr = node.bgp.ibgp_over_ebgp.get("rr",None)
      if not(rrlist) or node_is_rr:
        for name,n in topology.nodes.items():
          if "bgp" in n:
            if asn in n.bgp.ibgp_over_ebgp.get("as",{}) and n.name != node.name:
              # Except between RR nodes
              if not node_is_rr or not n.bgp.ibgp_over_ebgp.get("rr",None):
                node.bgp.neighbors.append( bgp_neighbor(n,'ibgp',asn,n.loopback) )
      #
      # The node is not a route reflector, and we have a non-empty RR list
      # We need BGP sessions with the route reflectors
      else:
        for n in rrlist:
          if n.name != node.name:
            node.bgp.neighbors.append( bgp_neighbor(n,'ibgp',asn,n.loopback) )

    #
    # eBGP sessions - iterate over all links, find adjacent nodes
    # in different AS numbers, and create BGP neighbors; set 'local_as'
    ibgp_as = topology.bgp['as']
    single_as = len(node.bgp.ibgp_over_ebgp['as']) == 1
    for l in node.get("interfaces",[]):
      for ngb_ifdata in l.get("neighbors",[]):
        ngb_name = ngb_ifdata.node
        neighbor = topology.nodes[ngb_name]
        if not "bgp" in neighbor:
          # print( f"ibgp-over-bgp: BGP not enabled for neighbor {ngb_name}" )
          continue

        # Iterate over both sets of AS; support at most 1 eBGP peering
        # print( f"ibgp-over-ebgp: Checking eBGP peering between {node.name} and {ngb_name}: {list(neighbor.bgp.ibgp_over_ebgp['as'])}" )
        for asn in node.bgp.ibgp_over_ebgp['as']:
          for asn2 in neighbor.bgp.ibgp_over_ebgp['as']:
            if (single_as or (asn!=ibgp_as and asn2!=ibgp_as)) and asn!=asn2:
              extra_data = Box({})
              extra_data.ifindex = l.ifindex
              extra_data.local_as = asn
              if "unnumbered" in l:
                extra_data.unnumbered = True
                extra_data.local_if = l.ifname
              # print( f"ibgp-over-ebgp: Found eBGP peer {asn}-{asn2} to {ngb_name}" )
              node.bgp.neighbors.append( bgp_neighbor(neighbor,'ebgp',asn2,ngb_ifdata,extra_data) )
              break # Stop at first eBGP peering
          else:
              continue # if inner loop did not break
          break # Exit outer loop

def post_transform(topology: Box) -> None:
  build_bgp_groups( topology ) # Update groups created by regular bgp module
  for node in topology.nodes.values():
    if 'bgp' in node:
        # Undo bgp module neighbor calculations, then rebuild them
        node.bgp.neighbors = []
        build_bgp_sessions(node,topology)

  # Cleanup
  for node in topology.nodes.values():
    if 'bgp' in node:
        node.bgp.pop('ibgp_over_ebgp')
