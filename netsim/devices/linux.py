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

    for intf in node.interfaces:
      if not intf.get('dhcp.client',False):
        continue
      log.error(
        f"Linux containers (node {node.name}) cannot run DHCP clients.",
        more_hints=[ "Use 'dhclient' or 'cumulus' device type" ],
        category=log.IncorrectType,
        module='quirks')
