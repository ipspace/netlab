#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
from box import Box

from . import _Quirks
from ..utils import log

class SRLINUX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'vrf' in mods:
        for _,vrf in node.get('vrfs', {}).items():
            if len(vrf['import']) > 1 or len(vrf['export']) > 1:
              if 'evpn' not in mods:
                log.error(
                    f'Inter-VRF route leaking on ({node.name}) only supported in combination with BGP EVPN.\n',
                    log.IncorrectType,
                    'quirks')
                return
