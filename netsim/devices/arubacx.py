#
# Aruba AOS-CX quirks
# # 
# # OSPF Process ID can only be 1-63.
# # When using VRFs, the process ID is taken from the vrfidx, which usually is > 100.
# # Here we are mapping every VRF to a specific ospfidx
#
from box import Box

from . import _Quirks
from ..augment import devices
from ..utils import log

class ARUBACX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'ospf' in mods and 'vrf' in mods:
        ospfidx = 2
        for vrf in node.get('vrfs', {}).keys():
            if ospfidx > 63:
                log.error(
                    f'Too many VRFs with OSPF in ({node.name}).\n',
                    log.IncorrectType,
                    'quirks')
                return
            node.vrfs[vrf]['ospfidx'] = ospfidx
            ospfidx = ospfidx + 1
