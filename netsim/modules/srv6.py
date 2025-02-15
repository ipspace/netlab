#
# SRv6 transformation module
#
from box import Box

from . import _Module
from ..utils import log
import ipaddress

class SRV6(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:

      # Could model this as another addressing pool too
      locator = f'{topology.defaults.srv6.locator}:{node.id:x}::/64'
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

      node.srv6.locator = locator
