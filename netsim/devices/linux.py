#
# Linux quirks
#
from box import Box

from . import _Quirks
from ..utils import log
from ..augment import devices

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
