#
# Linux quirks
#
from box import Box

from . import _Quirks
from ._common import check_indirect_static_routes
from ..utils import log
from ..augment import devices

class Linux(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)

    if devices.get_provider(node,topology) != 'clab':
      return

    if 'dhcp' in node.get('module',[]):
      log.error(
        f"netlab does not support DHCP functionality in Linux containers",
        more_hints=[ "Use 'cumulus' for DHCP client or 'dnsmasq' for DHCP server" ],
        category=log.IncorrectType,
        module='quirks')
