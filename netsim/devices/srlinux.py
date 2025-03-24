#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
from box import Box

from . import _Quirks,need_ansible_collection,report_quirk
from ..utils import log,routing as _routing

def check_prefix_deny(node: Box) -> None:
  for pf_name,pf_list in node.get('routing.prefix',{}).items():
    for p_entry in pf_list:
      if p_entry.get('action',None) == 'deny':
        report_quirk(
          text=f'SR Linux does not support "deny" action in prefix filters (node {node.name} prefix filter {pf_name})',
          node=node,
          quirk='prefix_deny',
          category=log.IncorrectValue)
        break

def cleanup_neighbor_transport(node: Box, topology: Box) -> None:
  for ngb in _routing.neighbors(node,vrf=True):
    pass

class SRLINUX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    dt = node.clab.type
    if dt in ['ixr6','ixr10','ixr6e','ixr10e'] and not node.clab.get('license',None):
      report_quirk(
        text=f'You need a valid SR Linux license to run {dt} container on node {node.name}',
        node=node,
        quirk='mpls_license',
        category=log.MissingValue)

    mods = node.get('module',[])
    if 'vrf' in mods and 'evpn' not in mods:
      vlist = []
      for vname,vrf in node.get('vrfs', {}).items():
        if len(vrf['import']) > 1 or len(vrf['export']) > 1:
          vlist.append(vname)

      if vlist:
        report_quirk(
          text=f'Inter-VRF route leaking is supported only in combination with BGP EVPN',
          more_data=[ f'Node {node.name} VRF(s) {",".join(vlist)}' ],
          node=node,
          quirk='vrf_route_leaking',
          category=log.IncorrectType)

    if 'isis' in mods:
      if node.get('isis.af.ipv6',False) and 'sr' in mods:
        report_quirk(
          text=f'SR Linux on "{node.name}" does not support IS-IS multi-topology for IPv6 in combination with segment routing',
          node=node,
          quirk='ipv6_sr')

    if 'bgp' in mods:
      cleanup_neighbor_transport(node,topology)
      for c,vals in topology.get('bgp.community',[]).items():
        if 'extended' not in vals:
          report_quirk(
            text=f'SR Linux on ({node.name}) does not support filtering out extended communities for BGP.',
            more_data= [ f'{c}:{vals}' ],
            node=node,
            category=Warning,
            quirk='bgp_community')

    if 'mpls' in mods or 'sr' in mods:
      if dt not in ['ixr6','ixr10','ixr6e','ixr10e']:
        report_quirk(
          text=f'SR Linux device type must be set to ixr6/ixr10 for MPLS to work (node {node.name})',
          node=node,
          category=log.IncorrectValue)

    if 'routing' in mods and node.get('routing.prefix',None):
      check_prefix_deny(node)
  
  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.srlinux',version='0.5.0')
