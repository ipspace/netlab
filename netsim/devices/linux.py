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
    provider = node.get('provider',None) or topology.provider
    if provider != 'clab':
      return

    print(f'Linux quirk {node.name} {provider}')
    for intf in node.interfaces:
      if not intf.get('dhcp.client',False):
        continue
      log.error(
        f"Linux containers (node {node.name}) cannot run DHCP clients.",
        more_hints=[ "Use 'dhclient' or 'cumulus' device type" ],
        category=log.IncorrectType,
        module='quirks')
