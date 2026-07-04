'''
Utility functions for point-to-point tunnels
'''

import typing

from box import Box

from ... import api
from ...augment import links as _links
from ...augment import nodes as _nodes
from ...utils import log
from .. import tunnel as _tunnel


def init(topology: Box) -> None:
  '''
  This module is a utility module. Nothing to see here, please move on ;)
  '''
  log.fatal("You cannot use the 'tunnel._p2p' plugin. Use a plugin for the tunnel mode you're interested in")

def feature_check(topology: Box, t_mode: str, t_desc: str) -> dict:
  '''
  Check whether the devices using tunnels support them. Returns a dictionary
  of nodes using the specified tunnel technology
  '''
  node_iflist: dict = {}

  for node,ndata in topology.nodes.items():
    t_iflist = [ intf for intf in _tunnel.interfaces(ndata,t_mode) ]
    if not t_iflist:                                        # No tunnel interfaces on this node?
      continue                                              # Cool, move on

    if not _tunnel.check_feature(ndata,topology,f_name=t_mode,f_desc=t_desc):
      continue                                              # Device does not support tunnel features, move on

    VRF_OK = True
    for intf in t_iflist:                                   # Next check: VRF features
      if not 'tunnel.vrf' in intf:                          # Tunnel does not use transport VRF? Cool, move on
        continue
      VRF_OK = _tunnel.check_feature(ndata,topology,f_name=t_mode,f_desc=f'VRF {t_desc}',f_value='vrf')
      break

    if not VRF_OK:                                          # If VRF check failed, move to next node
      continue

    node_iflist[node] = t_iflist
    api.node_config(ndata,f'tunnel.{t_mode}')               # Remember that we need to configure tunnels

  return node_iflist

def tunnel_source_interfaces(
      topology: Box,
      node_iflist: dict,
      default_af: typing.Optional[str] = None,
      t_name: str = '') -> typing.Generator[tuple[Box, Box], None, None]:
  '''
  Set tunnel._source on each tunnel interface and yield (ndata, intf) tuples
  for interfaces where the source lookup succeeded.

  Tunnel plugins can iterate over the generator to apply type-specific tweaks
  after the shared source data is in place.
  '''
  for node in node_iflist.keys():
    ndata = topology.nodes[node]
    for intf in node_iflist[node]:
      if 'tunnel.af' not in intf and default_af:
        intf.tunnel.af = default_af                         # Set the default AF for the tunnel

      u_iflist = _tunnel.get_tunnel_source(ndata,intf,topology)
      if not _tunnel.set_tunnel_source(intf,u_iflist,ndata,topology):
        continue

      if t_name:
        _tunnel.set_tunnel_name(intf,t_name)

      yield ndata,intf

def tunnel_source(
      topology: Box,
      node_iflist: dict,
      default_af: typing.Optional[str] = None,
      t_name: str = '') -> None:
  '''
  Iterate over nodes using tunnels and figures out the source interfaces
  for all tunnel interfaces

  - node_iflist: contains lists of tunnel interfaces (returned by tunnel_feature_check)
  - default_af:  has to be set for tunnels that are not dual-stack-aware
  - t_name:      the string to add to interface description once we know it's a valid tunnel
  '''
  for _ in tunnel_source_interfaces(topology,node_iflist,default_af,t_name):
    pass

def tunnel_destination(
      topology: Box,
      node_iflist: dict,
      t_mode: str) -> None:
  '''
  All nodes with tunnel interfaces should have tunnel._source interface
  values by now. Iterate over those nodes and use the neighbor
  tunnel._source values to set interface tunnel._destination.
  '''
  for node in node_iflist:                                  # Process only nodes with tunnel interfaces
    for intf in node_iflist[node]:                          # ... and only tunnel interfaces
      if len(intf.neighbors) != 1:
        linkname = _links.get_linkname(topology,intf.linkindex)
        log.error(
          f'Tunnel interface should have exactly one neighbor (found {len(intf.neighbors)})',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {linkname}',
          module=f'tunnel.{t_mode}',
          category=log.IncorrectValue)
        continue
      ngb = intf.neighbors[0]
      ngb_intf = _nodes.get_node_interface(topology.nodes[ngb.node],ifname=ngb.ifname)
      if not ngb_intf:
        log.error(
          f'Internal error: Cannot find the remote tunnel interface for interface {intf.ifname} on {node}',
          category=log.FatalError,
          module=f'tunnel.{t_mode}')
        continue
      if 'tunnel._source' not in ngb_intf:
        linkname = _links.get_linkname(topology,intf.linkindex)
        log.error(
          f'Cannot find tunnel destination for node {ngb.node}',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {linkname}',
          module=f'tunnel.{t_mode}',
          category=log.MissingDependency)
        continue

      intf.tunnel._destination = ngb_intf.tunnel._source
