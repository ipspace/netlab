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

DEFAULT_VPN_AF: dict = {
  'ipv4': [ 'ibgp' ],
  'ipv6': [ 'ibgp' ]
}

FEATURE_NAME: dict = {
  'ldp': 'LDP-based label distribution',
  'bgp': 'BGP Labeled Unicast',
  'vpn': 'MPLS/VPN'
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
    intf_ldp = data.get_from_box(intf,'mpls.ldp')
    if 'vrf' in intf:
      if not intf_ldp:
        continue
      if not features.mpls.csc:
        common.error(
          f'Device {node.device} does not support MPLS CsC (LDP in VRF) configured on {node.name}',
          common.IncorrectValue,
          'mpls')
        continue

    if not intf_ldp is None and 'mpls' in intf:
      data.bool_to_defaults(intf.mpls,'ldp')
      if 'ldp' in intf.mpls:
        intf.ldp = intf.mpls.ldp

    if not _routing.external(intf,'ldp'):
      _routing.passive(intf,'ldp')

  _routing.remove_unused_igp(node,'ldp')

def validate_mpls_bgp_parameter(node: Box, feature: str) -> bool:
  if isinstance(node.mpls[feature],list):
    session_list = node.mpls[feature]
    if not data.validate_list_elements(session_list,BGP_SESSIONS):
      common.error(
        f'Invalid BGP session type in nodes.{node.name}.mpls.{feature} parameter',
        common.IncorrectValue,
        'mpls')
      return False

    node.mpls[feature] = Box({})
    for af in node.af:
      node.mpls[feature][af] = session_list
  elif isinstance(node.mpls[feature],Box):
    for af in AF_LIST:
      if not af in node.mpls[feature]:
        continue

      if data.must_be_list(node.mpls[feature],af,f'nodes.{node.name}.mpls.{feature}') is None:
        return False

      if not data.validate_list_elements(node.mpls[feature][af],BGP_SESSIONS):
        common.error(
          f'Invalid BGP session type in nodes.{node.name}.mpls.{feature}.{af} parameter',
          common.IncorrectValue,
          'mpls')
        return False
  else:
    common.error(
      f'nodes.{node.name}.mpls.{feature} parameter must be a boolean, list, or dictionary',
      common.IncorrectValue,
      'mpls')
    return False

  return True

def node_adjust_bgplu(node: Box, topology: Box, features: Box) -> None:
  if not validate_mpls_bgp_parameter(node,'bgp'):
    return

  if not 'neighbors' in node.get('bgp',{}):
    return

  for n in node.bgp.neighbors:
    for af in ['ipv4','ipv6']:
      if af in n and af in node.mpls.bgp and n.type in node.mpls.bgp[af]:
        n[af+'_label'] = True

def prune_mplsvpn_af(setting: Box, node: Box) -> None:
  vrf_af :dict = {}

  for af in AF_LIST:
    for vdata in node.get('vrfs',{}).values():
      if af in vdata.af:
        vrf_af[af] = True
        break

  for af in AF_LIST:
    if af in setting and not af in vrf_af and not 'ebgp' in setting[af]:
      setting.pop(af,None)

def node_adjust_mplsvpn(node: Box, topology: Box, features: Box) -> None:
  if not validate_mpls_bgp_parameter(node,'vpn'):
    return

  if not node.bgp.get('rr',False):
    prune_mplsvpn_af(node.mpls.vpn,node)

  for n in node.bgp.neighbors:
    if 'ipv4' in n:
      for af in AF_LIST:
        if af in node.mpls.vpn:
          n['vpn'+af.replace('ip','')] = n.ipv4

class MPLS(_Module):

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global DEFAULT_BGP_LU
    if not 'mpls' in node:
      return

    data.bool_to_defaults(node.mpls,'ldp',{})
    if 'ldp' in node.mpls:
      data.must_be_bool(node.mpls.ldp,'disable_unlabeled',f'nodes.{node.name}.mpls.ldp')
      if not any(m in ['ospf','isis','eigrp'] for m in node.module):
        common.error(
          f'You cannot enable LDP on node {node.name} without an IGP',
          common.MissingValue,
          'mpls')

    data.bool_to_defaults(node.mpls,'bgp',DEFAULT_BGP_LU)
    data.bool_to_defaults(node.mpls,'vpn',DEFAULT_VPN_AF)
    if 'bgp' in node.mpls or 'vpn' in node.mpls:
      if not 'bgp' in node.module:
        common.error(
          f'You cannot enable BGP-LU or MPLS/VPN on node {node.name} without BGP module',
          common.MissingValue,
          'mpls')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    global FEATURE_NAME

    if not node.mpls:     
      return

    features = devices.get_device_features(node,topology.defaults)

    for fn in FEATURE_NAME.keys():
      if fn in node.mpls and not features.mpls[fn]:
        common.error(
          f'Device {node.device} used by {node.name} does not support {FEATURE_NAME[fn]}',
          common.IncorrectValue,
          'mpls')

    if 'ldp' in node.mpls:
      node_adjust_ldp(node,topology,features)

    if 'bgp' in node.mpls:
      node_adjust_bgplu(node,topology,features)

    if 'vpn' in node.mpls:
      node_adjust_mplsvpn(node,topology,features)
