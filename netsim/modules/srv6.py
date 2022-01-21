#
# SRv6 transformation module
#
from box import Box

from . import _Module
from .. import addressing, common
import ipaddr # type: ignore

class SRV6(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:

      # Could model this as another addressing pool too
      locator = ipaddr.IPv6Network( f'{topology.defaults.srv6.locator}:{node.id:x}::/64' )

      if 'ipv6' not in node.loopback:
          common.error( "SRv6 requires an ipv6 loopback address",
                        common.MissingValue, 'srv6' )
      elif locator.overlaps( ipaddr.IPNetwork(node.loopback.ipv6) ):
          common.error( f"Node ipv6 loopback address {node.loopback.ipv6} overlaps with locator {locator}",
                        common.IncorrectValue, 'srv6' )

      node.srv6.locator = str( locator )

      # TODO process per-interface srv6 parameters?
      # for l in node.get('interfaces',[]):
