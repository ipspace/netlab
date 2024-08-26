#
# Aruba AOS-CX quirks
# # 
# # OSPF Process ID can only be 1-63.
# # When using VRFs, the process ID is taken from the vrfidx, which usually is > 100.
# # Here we are mapping every VRF to a specific ospfidx
#
from box import Box

from . import _Quirks,need_ansible_collection
from ..augment import devices
from ..utils import log

class ARUBACX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    # Checks for OSPF Process ID (index based)
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
    # Remove OSPF default originate route-type (not supported, yet)
    if 'ospf' in mods:
      if 'default' in node.get('ospf', {}) and 'type' in node.ospf.default:
        del node.ospf.default['type']
        log.info(f'OSPF default-information originate (on node {node.name}) does not support metric-type attribute (on default routing table)',
                  'quirks')
    if 'ospf' in mods and 'vrf' in mods:
      for vname,vdata in node.get('vrfs', {}).items():
        if 'default' in vdata.get('ospf', {}) and 'type' in vdata.ospf.default:
          del vdata.ospf.default['type']
          log.info(f'OSPF default-information originate (on node {node.name}) does not support metric-type attribute (on vrf {vname})',
                    'quirks')
    
    # MPLS can be used only with 'external' provider
    if 'mpls' in mods and node.get('provider','') != 'external':
       log.error(
          f'ArubaCX MPLS data plane works only on physical devices (using the external provider)',
          log.IncorrectType,
          'quirks')

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'arubanetworks.aoscx')
