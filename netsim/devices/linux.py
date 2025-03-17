#
# Linux quirks
#
from box import Box

from . import _Quirks
from ._common import check_indirect_static_routes
from ..utils import log
from ..augment import devices

"""
The "routing" module is used to configure static routes pointing to the default
gateway. Linux configuration creates static routes as part of the initial
configuration template, so it makes no sense to keep the "routing" module active
on a Linux host if it's only used for static routes.
"""
def check_routing_module(node: Box) -> None:
  if 'routing' not in node.get('module',[]):      # The node is not using the routing module, nothing to do
    return

  if 'routing' not in node:                       # No routing data in the node
    return
  
  if 'routing' in node and list(node.routing.keys()) != [ 'static' ]:
    return                                        # There's other routing information, not just static routes

  node.module.remove('routing')                   # Remove the routing module from the node
  if not node.module:
    node.pop('module',None)

class Linux(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_routing_module(node)

    if devices.get_provider(node,topology) != 'clab':
      return

    if 'dhcp' in node.get('module',[]):
      log.error(
        f"netlab does not support DHCP functionality in Linux containers",
        more_hints=[ "Use 'cumulus' for DHCP client or 'dnsmasq' for DHCP server" ],
        category=log.IncorrectType,
        module='quirks')

