#
# SRv6 transformation module
#
import typing

from box import Box
from netsim.augment import addressing

from . import _Module
from ..utils import log
from .. import data
import ipaddress
import netaddr

DEFAULT_VPN_AF: typing.Final[dict] = {
  'ipv4': [ 'ibgp' ],
  'ipv6': [ 'ibgp' ]
}

"""
Checks for iBGP neighbors that require the IPv4 address family but do not have an IPv4 transport
"""
def configure_bgp_for_srv6(node: Box, topology: Box) -> None:
   srv6_bgp = node.get('srv6.vpn', {})
   for nb in node.get('bgp.neighbors',[]):
      for af in log.AF_LIST:
        if af in nb and nb.type in srv6_bgp[af]:
          nb['vpn'+af.replace('ip','')] = nb[af]
      if not nb.get('ipv4') and nb.activate.get('ipv4'): # Check if neighbor has no ipv4 address but IPv4 AF enabled
         nb.ipv4_rfc8950 = True

class SRV6(_Module):
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    data.bool_to_defaults(node.srv6,'vpn',DEFAULT_VPN_AF)

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
