#
# MPLS (LDP/BGP-LU) transformation module
#
import typing

from box import Box

from . import _Module,_routing
from .. import common
from ..common import AF_LIST,BGP_SESSIONS
from .. import data
from ..augment import devices

DEFAULT_BGP_LU: dict = {
  'ipv4': [ 'ibgp','ebgp' ],
  'ipv6': [ 'ibgp','ebgp' ]
}

def node_adjust_ldp(node: Box, topology: Box, features: Box) -> None:
  if not 'ipv4' in node.get('af',{}):
    common.error(
      f'You cannot enable MPLS LDP on node {node.name} without IPv4 address family',
      common.MissingValue,
      'mpls')
    return

  node.ldp = node.mpls.ldp
  node.mpls.pop('ldp',None)
  _routing.router_id(node,'ldp',topology.pools)

  for intf in node.get('interfaces',[]):
    if 'vrf' in intf and not features.mpls.csc:
      common.error(
        f'Device {node.device} does not support MPLS CsC (LDP in VRF) configured on {node.name}',
        common.IncorrectValue,
        'mpls')
      continue

    if 'mpls' in intf:
      data.bool_to_defaults(intf.mpls,'ldp')
      if 'ldp' in intf.mpls:
        intf.ldp = intf.mpls.ldp

    if not _routing.external(intf,'ldp'):
      _routing.passive(intf,'ldp')

  _routing.remove_unused_igp(node,'ldp')

def validate_mpls_bgp_parameter(node: Box, topology: Box, features: Box) -> bool:
  if isinstance(node.mpls.bgp,list):
    session_list = node.mpls.bgp
    if not data.validate_list_elements(session_list,BGP_SESSIONS):
      common.error(
        f'Invalid BGP session type in nodes.{node.name}.mpls.bgp parameter',
        common.IncorrectValue,
        'mpls')
      return False

    node.mpls.bgp = Box({})
    for af in node.af:
      node.mpls.bgp[af] = session_list
  elif isinstance(node.mpls.bgp,Box):
    for af in AF_LIST:
      if not af in node.mpls.bgp:
        continue

      if data.must_be_list(node.mpls.bgp,af,f'nodes.{node.name}.mpls.bgp') is None:
        return False

      if not data.validate_list_elements(node.mpls.bgp[af],BGP_SESSIONS):
        common.error(
          f'Invalid BGP session type in nodes.{node.name}.mpls.bgp.{af} parameter',
          common.IncorrectValue,
          'mpls')
        return False
  else:
    common.error(
      f'nodes.{node.name}.mpls.bgp parameter must be a boolean, list, or dictionary',
      common.IncorrectValue,
      'mpls')
    return False

  return True

def node_adjust_bgplu(node: Box, topology: Box, features: Box) -> None:
  if not validate_mpls_bgp_parameter(node,topology,features):
    return

  if not 'neighbors' in node.get('bgp',{}):
    return

  for n in node.bgp.neighbors:
    for af in ['ipv4','ipv6']:
      if af in n and af in node.mpls.bgp and n.type in node.mpls.bgp[af]:
        n[af+'_label'] = True

class MPLS(_Module):

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global DEFAULT_BGP_LU
    if not 'mpls' in node:
      return

    data.bool_to_defaults(node.mpls,'ldp',{})
    if 'ldp' in node.mpls:
      if not any(m in ['ospf','isis','eigrp'] for m in node.module):
        common.error(
          f'You cannot enable LDP on node {node.name} without an IGP',
          common.MissingValue,
          'mpls')

    data.bool_to_defaults(node.mpls,'bgp',DEFAULT_BGP_LU)
    if 'bgp' in node.mpls:
      if not 'bgp' in node.module:
        common.error(
          f'You cannot enable BGP-LU on node {node.name} without an BGP',
          common.MissingValue,
          'mpls')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)

    if not 'mpls' in node:
      return

    if 'ldp' in node.mpls:
      if not features.mpls.ldp:
        common.error(
          f'Device {node.device} used by {node.name} does not support LDP',
          common.IncorrectValue,
          'mpls')
      else:
        node_adjust_ldp(node,topology,features)

    if 'bgp' in node.mpls:
      if not features.mpls.bgp:
        common.error(
          f'Device {node.device} used by {node.name} does not support BGP Labeled Unicast',
          common.IncorrectValue,
          'mpls')
      else:
        node_adjust_bgplu(node,topology,features)
