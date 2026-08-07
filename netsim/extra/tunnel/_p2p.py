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

def feature_check(
      topology: Box,
      t_mode: str,                      # Tunnel mode, used primarily for error messages
      t_desc: str,                      # Tunnel mode description, used primarily for error messages
      t_af: bool = False,               # Do we need to check transport AF?
      t_default_af: str = '',           # Default transport AF
      ) -> dict:
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

    check_OK = True
    if t_af:                                                # Do we have to check the transport AF support?
      for u_af in ['ipv4','ipv6']:                          # Check IPv4 and IPv6
        for intf in t_iflist:
          tpt_af = intf.get('tunnel.af',t_default_af)       # Try to get the tunnel transport AF
          if tpt_af != u_af:                                # Not the one we're interested in? Move on
            continue
          if not _tunnel.check_feature(                     # Check the AF feature
                    ndata,
                    topology,
                    f_name=t_mode,
                    f_desc=f'{t_desc} over {u_af}',
                    f_value=u_af):
            check_OK = False                                # Mark the failure if needed
          break                                             # And get out of the interface loop

    for intf in t_iflist:                                   # Next check: VRF features
      if not 'tunnel.vrf' in intf:                          # Tunnel does not use transport VRF? Cool, move on
        continue
      if not _tunnel.check_feature(                         # Check the VRF feature
                ndata,
                topology,
                f_name=t_mode,
                f_desc=f'VRF {t_desc}',f_value='vrf'):
        check_OK = False                                    # Missing? Mark the failure
      break                                                 # And get out of the interface loop

    if not check_OK:                                        # If any advanced check failed, move to next node
      continue

    node_iflist[node] = t_iflist
    api.node_config(ndata,f'tunnel.{t_mode}')               # Remember that we need to configure tunnels

  return node_iflist

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
  for node in node_iflist.keys():
    ndata = topology.nodes[node]
    for intf in node_iflist[node]:
      if 'tunnel.af' not in intf and default_af:
        intf.tunnel.af = default_af                         # Set the default AF for the tunnel

      u_iflist = _tunnel.get_tunnel_source(ndata,intf,topology)
      if not u_iflist:                                      # The error message was already generated
        continue
      if not _tunnel.set_tunnel_source(intf,u_iflist,ndata,topology):
        continue

      if t_name:
        _tunnel.set_tunnel_name(intf,t_name)

def tunnel_destination(
      topology: Box,
      node_iflist: dict,
      t_mode: str,
      mtu_adjust: typing.Optional[dict] = None) -> None:
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
      if 'mtu' in intf or not mtu_adjust:                   # Did user set the tunnel MTU? Can we adjust it?
        continue                                            # ... no luck, move on

      t_af = intf.get('tunnel.af','unknown')                # Get the transport AF (it impacts the overhead)
      if mtu_adjust and t_af in mtu_adjust:                 # Do we know how much?
        mtu = min(intf.get('tunnel._source.mtu',1500),ngb_intf.get('tunnel._source.mtu',1500))
        intf.mtu = mtu - mtu_adjust[t_af]                   # Adjust the tunnel MTU to the min of local/remote MTU - overhead
