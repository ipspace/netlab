#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
import re

from box import Box

from ..utils import log
from ..utils import routing as _routing
from . import _Quirks, need_ansible_collection, report_quirk


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

'''
Remove unused IPv4/IPv6 transport addresses -- SR Linux does not like a
BGP neighbor with no active address families
'''
def cleanup_neighbor_transport(node: Box, topology: Box) -> None:
  for ngb in _routing.neighbors(node,vrf=True):
    if 'local_if' in ngb:               # True unnumbered, move on
      continue
    ipv4 = ngb.get('ipv4',None)
    if ipv4 is True:                    # Could be RFC 8950 over numbered IPv6, move on
      continue

    # Remove IPv6 transport session if IPv6 is not activated
    for af in ['ipv4','ipv6']:
      if af not in ngb:                 # Do we have the neighbor IP address in this address family?
        continue
      if not isinstance(ngb[af],str):   # Is it a string (real IP address)?
        continue
      if ngb.activate.get(af,False):    # Is the AF activated?
        continue

      if af == 'ipv4':
        x_af = [ af for af in ['evpn','vpnv4','vpnv6','6pe'] if af in ngb ]
        if x_af:                        # Do we have extra address families running over IPv4 transport?
          continue

      report_quirk(
        text=f'Removed {af} transport address {ngb[af]} for BGP neighbor {ngb.name} on node {node.name}',
        more_hints=['No BGP address family was activated for this BGP neighbor'],
        quirk='bgp_transport',
        node=node,
        category=Warning)
      ngb.pop(af)

"""
Determines the SRL version based on the container image
"""
def set_api_version(node: Box) -> None:
  version = re.search(r'^.*/srlinux:([\d]+.[\d]+).*$', node.box)
  node._srl_version = [ 25, 3 ]         # Assume 25.3 release
  if version is not None:               # If we managed to match the SR Linux image name
    try:                                # ... try to extract release info into a list of ints
      node._srl_version = [ int(v) for v in version.group(1).split('.') ]
    except:                             # Extraction process failed?
      pass                              # ... no worries, we'll use the default

def check_nssa_default_cost(node: Box) -> None:
  for (odata,_,_) in _routing.rp_data(node,'ospf'):
    if 'areas' not in odata:
      continue
    for area in odata.areas:
      if area.kind != 'nssa':
        continue
      cost = area.get('default.cost')
      if cost:
        report_quirk(
          f'{node.name} cannot apply a default cost ({cost}) to NSSA area {area.area}',
          more_hints = [ 'Nokia SR Linux cannot configure a default-metric for NSSA areas' ],
          node=node,
          category=Warning,
          quirk='ospf_nssa_default_cost')

class SRLINUX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    dt = node.clab.type
    set_api_version(node)
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
      if node._srl_version < [ 25, 3 ]:
        for c,vals in topology.get('bgp.community',[]).items():
          if 'extended' not in vals:
            report_quirk(
              text=f'SR Linux on ({node.name}) before version 25.3.1 does not support filtering out extended communities for BGP.',
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

    if 'ospf' in mods:
      check_nssa_default_cost(node)
  
  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.srlinux',version='0.5.0')
