#
# SRv6 transformation module
#
import typing

from box import Box
from ..augment import addressing,devices

from . import _Module
from ..utils import log
from .. import data
import ipaddress

DEFAULT_VPN_AF: typing.Final[dict] = {
  'ipv4': [ 'ibgp' ],
  'ipv6': [ 'ibgp' ]
}

"""
Configures BGP VPN address families for neighbors, and extended nexthop where needed
"""
def configure_bgp_for_srv6(node: Box, topology: Box) -> None:
   srv6_bgp = node.get('srv6.vpn', {})
   for nb in node.get('bgp.neighbors',[]):
      for af in DEFAULT_VPN_AF.keys():
        if nb.type in srv6_bgp[af]:
          vpn_af = 'vpn'+af.replace('ip','')
          if node.af.get(vpn_af): # Check if the VPN AF is enabled
            if af in nb:
              nb[vpn_af] = nb[af] # Use the corresponding transport if available
            elif af=='ipv4':      # VPNv4 over ipv6 requires RFC8950 extended next hops
              nb[vpn_af] = nb.ipv6
              nb.ipv4_rfc8950 = True     

class SRV6(_Module):
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    d_features = devices.get_device_features(node,topology.defaults)
    if node.srv6.get('bgp'):
      if not d_features.srv6.get('bgp') or 'bgp' not in mods:
        log.warning(
          f"Node {node.name} does not support BGP with SRv6, or has the module disabled",
          module='srv6')
        node.srv6.bgp = False
    for igp in node.get('srv6.igp',[]):
      if igp not in mods:
        log.error(
          f"Node {node.name} does not have the {igp} IGP module enabled to run SRv6",
          category=log.MissingDependency,
          module='srv6')
      if not d_features.srv6.get(igp):
        log.error(
          f"Node {node.name} (device {node.device}) does not support {igp} as IGP for SRv6",
          category=log.IncorrectValue,
          module='srv6')
      
    data.bool_to_defaults(node.srv6,'vpn',DEFAULT_VPN_AF)
    if node.srv6.get('vpn') and 'vrf' not in mods:
      log.error(
          f"Node {node.name} does not have the VRF module enabled to support BGP VPN",
          category=log.MissingDependency,
          module='srv6')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    locator = node.get('srv6.locator')
    if not locator:
       prefix = addressing.get(topology.pools,['srv6_locator'])['ipv6']
       locator = str(prefix)
       node.srv6.locator = locator
    locator_net = ipaddress.IPv6Network(locator)
    if 'ipv6' not in node.loopback:
      log.error(
        f"SRv6 requires an ipv6 loopback address on node {node.name}",
        category=log.MissingValue,
        module='srv6')
    elif ipaddress.IPv6Interface(node.loopback.ipv6).network.subnet_of(locator_net):
      log.error(
        f"Node {node.name} ipv6 loopback address {node.loopback.ipv6} overlaps with locator {locator}",
        category=log.IncorrectValue,
        module='srv6')
    if 'bgp' in node and node.srv6.get('vpn'):
      configure_bgp_for_srv6(node,topology)
