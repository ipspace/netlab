#
# BGP neighbors transformation module to support a different underlay AS per node
#
# The core bgp module only supports a single AS per node, as that is the more
# common and simple way to operate BGP. Most vendors/devices can support
# multiple AS, for example in a topology that uses iBGP for an EVPN overlay and
# eBGP for the underlay.
#
# It is assumed the core bgp module provides the iBGP overlay peerings. This
# module adds an 'underlay_as' per node, and builds additional eBGP peerings
# based on that attribute.
#
# Changes:
# * Creates additional bgp.neighbors of type 'ebgp' with a 'local_as' attribute
#
import typing, netaddr
from box import Box
from netsim import common

"""
Adds a custom bgp.underlay_as node attribute
"""
def init(topology: Box) -> None:
    # Allow users to specify a different AS to use for underlay peering (eBGP)
    topology.defaults.bgp.attributes.node.append('underlay_as')

    # Also allow the AS to be overriden on a per-link basis
    topology.defaults.bgp.attributes.link.append('underlay_as')

def ebgp_neighbor(n: Box, asn: int, intf: Box, extra_data: dict) -> Box:
  ngb = Box(extra_data,default_box=True,box_dots=True)
  ngb.name = n.name
  ngb.type = 'ebgp'
  ngb["as"] = asn  # 'as' for backwards compatibility, would prefer 'peer_as'
  for af in ["ipv4","ipv6"]:
    if af in intf:
      if "unnumbered" in ngb and ngb.unnumbered == True:
        ngb[af] = True
      elif isinstance( intf[af], bool ):
        ngb[af] = intf[af]
      else:
        ngb[af] = str(netaddr.IPNetwork(intf[af]).ip)
  return ngb


"""
build_ebgp_sessions: augment BGP neighbors with ebgp peers
* EBGP sessions are established whenever two nodes on the same link have
  different underlay AS
"""
def build_ebgp_sessions(node: Box, topology: Box) -> None:

    #
    # eBGP sessions - iterate over all links, find adjacent nodes
    # in different AS numbers, and create eBGP neighbors; set 'local_as'
    ibgp_as = topology.bgp['as']
    for l in [ l for l in node.get("interfaces",[]) if l.type == 'p2p' ]:
      node_as = l.bgp.underlay_as if "bgp" in l and "underlay_as" in l.bgp else node.bgp.underlay_as

      for ngb_ifdata in l.get("neighbors",[]):
        ngb_name = ngb_ifdata.node
        neighbor = topology.nodes[ngb_name]
        if not "bgp" in neighbor:
          continue

        if "bgp" in ngb_ifdata and "underlay_as" in ngb_ifdata.bgp:
          peer_as = ngb_ifdata.bgp.underlay_as
        elif "underlay_as" in neighbor.bgp:
          peer_as = neighbor.bgp.underlay_as
        else:
          continue # No underlay_as defined for this neighbor

        if node_as!=peer_as:
          extra_data = Box({})
          extra_data.ifindex = l.ifindex
          if node_as != ibgp_as:
            extra_data.local_as = node_as
          if "unnumbered" in l:
            extra_data.unnumbered = True
            extra_data.local_if = l.ifname
          if common.DEBUG:
            print(f'ebgp-local_as: adding neighbor for node {node.name} peer {neighbor.name} peer_as={peer_as}')
          node.bgp.neighbors.append( ebgp_neighbor(neighbor,peer_as,ngb_ifdata,extra_data) )

def post_transform(topology: Box) -> None:
  for node in topology.nodes.values():
    if "bgp" in node and "underlay_as" in node.bgp:
        build_ebgp_sessions(node,topology)
