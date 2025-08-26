#
# Aruba AOS-CX quirks
# # 
# # OSPF Process ID can only be 1-63.
# # When using VRFs, the process ID is taken from the vrfidx, which usually is > 100.
# # Here we are mapping every VRF to a specific ospfidx
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk


class ARUBACX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    n_provider = devices.get_provider(node,topology.defaults)
    mods = node.get('module',[])
    # Checks for OSPF Process ID (index based)
    if 'ospf' in mods and 'vrf' in mods:
      ospfidx = 2
      for vrf in node.get('vrfs', {}).keys():
        if ospfidx > 63:
          report_quirk(
            text=f'Too many VRFs with OSPF in ({node.name})',
            node=node,
            category=log.IncorrectValue)
          break
        node.vrfs[vrf]['ospfidx'] = ospfidx
        ospfidx = ospfidx + 1

    # Remove OSPF default originate route-type (not supported, yet)
    if 'ospf' in mods:
      if 'default' in node.get('ospf', {}) and 'type' in node.ospf.default:
        del node.ospf.default['type']
        report_quirk(
           text=f'OSPF default-information originate (used in global routing table on node {node.name}) does not support metric-type attribute',
           node=node,
           quirk='ospf_default_type',
           category=Warning)

    if 'ospf' in mods and 'vrf' in mods:
      for vname,vdata in node.get('vrfs', {}).items():
        if 'default' in vdata.get('ospf', {}) and 'type' in vdata.ospf.default:
          del vdata.ospf.default['type']
          report_quirk(
            text=f'OSPF default-information originate (used in VRF {vname} on node {node.name}) does not support metric-type attribute',
            node=node,
            quirk='ospf_default_type',
            category=Warning)
    
    # MPLS can be used only with 'external' provider
    if 'mpls' in mods and n_provider != 'external':
       report_quirk(
          text=f'MPLS data plane used on node {node.name} works only on physical devices',
          more_hints=['Use a physical switch with the external provider'],
          node=node,
          category=log.IncorrectType)
    
    # VNI must be below 65536
    if 'vlans' in node and n_provider != 'external':
      for vname,vdata in node.get('vlans',{}).items():
        if vdata.get('vni',0) > 65535:
          report_quirk(
            text=f'VLAN {vname} used on ArubaCX node {node.name} has VXLAN VNI {vdata.vni}',
            more_hints=['ArubaCX does not work correctly with VNI values above 65535'],
            node=node,
            quirk='vxlan_vni',
            category=log.IncorrectValue)

    # LAG + VSX quirks
    ## on VSX, you **must** configure the switch role as primary or secondary.
    ### The roles do not indicate which device is forwarding traffic at a given time as VSX is an active-active forwarding solution.
    ### The roles are used to determine which device stays active when there is a VSX split.
    ### -- HERE we will assume the first device found for a specific peer-link is the primary, and the second one is the secondary.
    if 'lag' in mods:
      # find my MC-LAG
      for intf in node.get('interfaces', []):
        pgroup = intf.get('lag', {}).get('mlag', {}).get('peergroup', False)
        if not pgroup:
          continue
        log.info(f'ArubaCX VSX: Found MLAG ID {pgroup} on node {node.name}')
        # search for another ArubaCX peer with same MLAG ID and _vsx_role set to 'primary'
        for n,nattrs in topology.nodes.items():
          if n == node.name:
            continue
          if nattrs.device != 'arubacx':
            continue
          for n_intf in nattrs.get('interfaces', []):
            n_pgroup = n_intf.get('lag', {}).get('mlag', {}).get('peergroup', False)
            if not n_pgroup:
              continue
            if n_pgroup == pgroup:
              # I have found my peer. Verify if it's the primary.
              _vsx_role = n_intf.get('lag', {}).get('mlag', {}).get('_vsx_role', '')
              my_role = 'primary'
              if _vsx_role == 'primary':
                my_role = 'secondary'
              log.info(f'  - MLAG Peer is node {n} (ID {pgroup}) - which has role: "{_vsx_role}" - setting my role to "{my_role}"')
              intf.lag.mlag._vsx_role = my_role

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'arubanetworks.aoscx')
