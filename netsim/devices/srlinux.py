#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
from box import Box

from . import _Quirks,need_ansible_collection
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
                break

    if 'isis' in mods:
      if node.get('isis.af.ipv6',False):
         log.error(
                    f'SR Linux on ({node.name}) does not support IS-IS multi-topology required for ipv6.\n',
                    log.IncorrectType,
                    'quirks')

    if 'bgp' in mods:
      for c,vals in topology.get('bgp.community',[]).items():
        if 'extended' not in vals:
           log.error(
                      f'SR Linux on ({node.name}) does not support filtering out extended communities for BGP. {c}:{vals}\n',
                      Warning,
                      'quirks')

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.grpc')
