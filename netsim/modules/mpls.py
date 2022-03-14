#
# MPLS (LDP/BGP-LU) transformation module
#
import typing

from box import Box

from . import _Module,_routing
from .. import common
from ..augment import devices

DEFAULT_BGP_LU: dict = {
  'ipv4': [ 'ibgp','ebgp' ],
  'ipv6': [ 'ibgp','ebgp' ]
}

def node_adjust_ldp(node: Box, topology: Box, features: Box) -> None:
  if not 'ldp' in node.mpls:
    return

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
      _routing.upgrade_boolean_setting(intf.mpls,'ldp')
      if 'ldp' in intf.mpls:
        intf.ldp = intf.mpls.ldp
        
    if not _routing.external(intf,'ldp'):
      _routing.passive(intf,'ldp')

  _routing.remove_unused_igp(node,'ldp')

def validate_mpls_bgp_parameter(node: Box, topology: Box, features: Box) -> bool:
  if isinstance(node.mpls.bgp,list):
    session_list = node.mpls.bgp
    if not _routing.validate_bgp_session_types(session_list):
      common.error(
        f'Invalid BGP session type in nodes.{node.name}.mpls.bgp parameter',
        common.IncorrectValue,
        'mpls')
      return False

    node.mpls.bgp = {}
    for af in node.af:
      node.mpls.bgp[af] = session_list
  elif isinstance(node.mpls.bgp,dict):
    for af in node.mpls.bgp.keys():
      if common.must_be_list(node.mpls.bgp,af,f'nodes.{node.name}.mpls.bgp') is None:
        return False

      if not _routing.validate_bgp_session_types(node.mpls.bgp[af]):
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
  if not 'bgp' in node.mpls:
    return

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

    _routing.upgrade_boolean_setting(node.mpls,'ldp',{})
    if 'ldp' in node.mpls:
      if not any(m in ['ospf','isis','eigrp'] for m in node.module):
        common.error(
          f'You cannot enable LDP on node {node.name} without an IGP',
          common.MissingValue,
          'mpls')

    _routing.upgrade_boolean_setting(node.mpls,'bgp',DEFAULT_BGP_LU)
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

    node_adjust_ldp(node,topology,features)
    node_adjust_bgplu(node,topology,features)
