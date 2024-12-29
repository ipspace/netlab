#
# Linux quirks
#
from box import Box

from . import _Quirks
from ..utils import log
from ..augment import devices

def check_indirect_static_routes(node: Box) -> None:
  for sr_entry in node.get('routing.static',[]):
    if 'intf' not in sr_entry.nexthop:
      log.error(
        f'Linux (node {node.name}) does not support static routes to non-connected next hops',
        more_data=f'Static route data: {sr_entry}',
        category=log.IncorrectType,
        module='quirks')

class Linux(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if devices.get_provider(node,topology) != 'clab':
      return

    if 'dhcp' in node.get('module',[]):
      log.error(
        f"netlab does not support DHCP functionality in Linux containers",
        more_hints=[ "Use 'cumulus' for DHCP client or 'dnsmasq' for DHCP server" ],
        category=log.IncorrectType,
        module='quirks')

    if node.get('routing.static',[]):
      check_indirect_static_routes(node)