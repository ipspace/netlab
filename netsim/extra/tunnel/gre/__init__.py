
from box import Box

from netsim import api
from netsim.augment import links as _links
from netsim.augment import nodes as _nodes
from netsim.utils import log
from netsim.utils import tunnel as _tunnel

_config_name = 'tunnel.gre'

def pre_link_transform(topology: Box) -> None:
  '''
  pre_link_transform hook: set tunnel link type, check whether GRE tunnels are P2P
  '''
  _tunnel.set_tunnel_type(topology)
  for link in _tunnel.links(topology,'gre'):
    if len(link.interfaces) != 2:
      log.error(
        f'A GRE tunnel must have exactly two nodes attached to it (link {link._linkname})',
        category=log.IncorrectAttr,
        module='tunnel.gre')

def get_linkname(topology: Box, linkindex: int) -> str:
  '''
  Utility function: get the name of a link referenced in an interface.
  Return 'unknown' when the link cannot be found
  '''
  link = _links.get_link_by_index(topology,linkindex)
  return link._linkname if link is not None else 'unknown'

def post_transform(topology: Box) -> None:
  '''
  post_transform hook: check device support, set tunnel interface source/destination
  '''
  node_iflist: dict = {}

  # First pass, check feature support and set source interfaces
  #
  for node,ndata in topology.nodes.items():
    first = True
    vrf_check = False
    node_iflist[node] = []

    # Initial interface pass: collect tunnel interfaces, check features
    #
    for intf in _tunnel.interfaces(ndata,'gre'):
      if first:
        first = False
        if not _tunnel.check_feature(ndata,topology,f_name='gre',f_desc='GRE tunnels'):
          break
        api.node_config(ndata,_config_name)

      if not vrf_check and 'tunnel.vrf' in intf:
        vrf_check = True
        if not _tunnel.check_feature(ndata,topology,f_name='gre',f_desc='VRF GRE tunnels',f_value='vrf'):
          break

      node_iflist[node].append(intf)

    # Process tunnel interfaces: set transport AF, tunnel name, and tunnel source
    #
    for intf in node_iflist[node]:
      if 'tunnel.af' not in intf:
        intf.tunnel.af = 'ipv4'                             # Assume IPv4 tunnel

      src_intf = _tunnel.get_tunnel_source(ndata,intf,topology)
      if src_intf:
        intf.tunnel._source = src_intf
      else:
        log.error(
          f'Cannot get {intf.tunnel.af} tunnel source for link {get_linkname(topology,intf.linkindex)} on node {node}',
          more_data=f'Tunnel source data: {intf.tunnel.source if "tunnel.source" in intf else "none"}',
          category=log.MissingDependency,
          module='tunnel')
        continue

      if 'name' in intf and '->' in intf.name and 'GRE' not in intf.name:
        intf.name += ' [GRE tunnel]'

  if log.get_error_count():                                 # Has someone reported an error?
    return                                                  # Might have been us, no reason to continue

  # Second pass -- after computing tunnel source for all GRE interfaces, set tunnel destinations
  #
  for node in node_iflist:                                  # Process only nodes with tunnel interfaces
    ndata = topology.nodes[node]                            # Get node data (we might need it)
    for intf in node_iflist[node]:                          # ... and only tunnel interfaces
      if len(intf.neighbors) != 1:
        log.error(
          f'GRE tunnel interface should have exactly one neighbor (found {len(intf.neighbors)})',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.gre',
          category=log.IncorrectValue)
        continue
      ngb = intf.neighbors[0]
      ngb_intf = _nodes.get_node_interface(topology.nodes[ngb.node],ifname=ngb.ifname)
      if not ngb_intf:
        log.error(
          f'Internal error: Cannot find the remote tunnel interface for interface {intf.ifname} on {node}',
          category=log.FatalError,
          module='tunnel.gre')
        continue
      if 'tunnel._source' not in ngb_intf:
        log.error(
          f'Cannot find tunnel destination for node {ngb.node}',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.gre',
          category=log.MissingDependency)
        continue

      intf.tunnel._destination = ngb_intf.tunnel._source
