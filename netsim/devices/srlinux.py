#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
from box import Box

from . import _Quirks,need_ansible_collection
from ..utils import log

def check_prefix_deny(node: Box) -> None:
  for pf_name,pf_list in node.get('routing.prefix',{}).items():
    for p_entry in pf_list:
      if p_entry.get('action',None) == 'deny':
        log.error(
          f'SR Linux does not support "deny" action in prefix filters (node {node.name} prefix filter {pf_name})',
          log.IncorrectValue,
          'quirks')
        break

class SRLINUX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    dt = node.clab.type
    if dt in ['ixr6','ixr10','ixr6e','ixr10e'] and not node.clab.get('license',None):
      log.error(
        f'You need a valid SR Linux license to run {dt} container on node {node.name}',
        log.MissingValue,
        'quirks')

    mods = node.get('module',[])
    if 'vrf' in mods:
        for _,vrf in node.get('vrfs', {}).items():
            if len(vrf['import']) > 1 or len(vrf['export']) > 1:
              if 'evpn' not in mods:
                log.error(
                    f'Inter-VRF route leaking on ({node.name}) only supported in combination with BGP EVPN',
                    log.IncorrectType,
                    'quirks')
                break

    if 'isis' in mods:
      if node.get('isis.af.ipv6',False) and 'sr' in mods:
         log.error(
            f'SR Linux on ({node.name}) does not support IS-IS multi-topology for IPv6 in combination with segment routing',
            Warning,
            'quirks')

    if 'bgp' in mods:
      for c,vals in topology.get('bgp.community',[]).items():
        if 'extended' not in vals:
           log.error(
              f'SR Linux on ({node.name}) does not support filtering out extended communities for BGP. {c}:{vals}',
              Warning,
              'quirks')

    if 'mpls' in mods or 'sr' in mods:
      if dt not in ['ixr6','ixr10','ixr6e','ixr10e']:
        log.error(
          f'SR Linux device type must be set to ixr6/ixr10 for MPLS to work (node {node.name})',
          log.IncorrectValue,
          'quirks')

    if 'routing' in mods and node.get('routing.prefix',None):
      check_prefix_deny(node)
  
  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.srlinux',version='0.5.0')
