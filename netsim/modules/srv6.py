#
# SRv6 transformation module
#
from box import Box

from . import _Module
from .. import addressing, common
import netaddr

class SRV6(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:

      # Could model this as another addressing pool too
      locator = netaddr.IPNetwork( f'{topology.defaults.srv6.locator}:{node.id:x}::/64' )

      if 'ipv6' not in node.loopback:
        common.error( f"SRv6 requires an ipv6 loopback address on node {node.name}",
                      common.MissingValue, 'srv6' )
      elif netaddr.IPNetwork(node.loopback.ipv6) in locator:
        common.error( f"Node {node.name} ipv6 loopback address {node.loopback.ipv6} overlaps with locator {locator}",
                      common.IncorrectValue, 'srv6' )

      node.srv6.locator = str( locator )

      # TODO process per-interface srv6 parameters?
      # for l in node.get('interfaces',[]):
