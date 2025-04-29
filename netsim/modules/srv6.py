#
# SRv6 transformation module
#
from box import Box

from . import _Module
from ..utils import log
import ipaddress

"""
Checks for iBGP neighbors that require the IPv4 address family but do not have an IPv4 transport
"""
def ibgp_enable_rfc8950(node: Box) -> None:
   for nb in node.get('bgp.neighbors',[]):
      if nb.type == 'ebgp':                          # Skip eBGP neihgbors
         continue
      if not nb.get('ipv4'):
         if nb.activate.get('ipv4'):                 # Check if neighbor has no ipv4 address but IPv4 AF enabled
           nb.ipv4_rfc8950 = True
         for af in log.AF_LIST:
           if af in node.mpls.vpn:
             nb['vpn'+af.replace('ip','')] = nb.ipv6 # Netlab only supports ipv4

def configure_bgp_for_srv6(node: Box) -> None:
   ibgp_enable_rfc8950(node)

class SRV6(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:

      # Could model this as another addressing pool too
      locator = f'{topology.defaults.srv6.locator}:{node.id:x}::/48'
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

      if node.get('srv6.locator')==topology.defaults.srv6.locator: # Allow user to specify one per node
        node.srv6.locator = locator

      if 'bgp' in node and node.srv6.get('bgp'):
         configure_bgp_for_srv6(node)
