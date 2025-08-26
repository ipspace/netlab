#
# Cumulus NVUE quirks
#
from box import Box

from ..augment import devices
from ..utils import log
from ..utils import routing as _rp_utils
from . import _Quirks, report_quirk

# from .cumulus import Cumulus  # This causes Cumulus_Nvue to get skipped
from .cumulus import check_ospf_vrf_default


def nvue_check_stp_features(node: Box, topology: Box) -> None:
  err_data = []
  stp_protocol = topology.get('stp.protocol','stp')
  for i in node.interfaces:
    if 'stp' not in i:
      continue
    if 'port_priority' in i.stp:  # AttributeNotImplemented("mstpctl-treeportprio") in NVUE
      if 'vlan' not in i:
        err_data.append(f'Non-VLAN interface {i.ifname}')
      elif stp_protocol!='pvrst':
        err_data.append(f'VLAN interface without PVRST {i.ifname}')

  if stp_protocol!='pvrst':
    for i in node.interfaces:
      if not i.get('vlan.trunk',{}):
        continue
      for vname,vdata in i.vlan.trunk.items():
        if 'stp' in vdata and 'port_priority' in vdata.stp:  # AttributeNotImplemented("mstpctl-treeportprio") in NVUE
          err_data.append(f'Trunk VLAN {vname} interface without PVRST {i.ifname}({i.get("name","?")})')


  if err_data:
    report_quirk(
      f'node {node.name} does not support STP port_priority on non-VLAN interfaces or without PVRST ({stp_protocol})',
      quirk='stp_port_priority',
      more_data=err_data,
      node=node)

"""
Checks for OSPFv3 which is not supported by NVUE configuration command
"""
def nvue_check_ospfv3(node: Box) -> None:
  if node.get('ospf.af.ipv6',False):
    report_quirk(
      text=f"Node '{node.name}' uses OSPFv3 which cannot be configured through Cumulus NVUE",
      more_hints=[ "Use a regular 'cumulus' node instead" ],
      node=node,
      category=log.IncorrectType)

"""
Checks for mixed trunk interfaces with native routed vlan. That doesn't work because the parent interface gets added
to the VLAN-aware bridge
"""
def nvue_check_native_routed_on_mixed_trunk(node: Box, topology: Box) -> None:
  for i in list(node.interfaces):
    if '_vlan_native' not in i:
      continue
    native_vlan = topology.vlans[ i._vlan_native ]
    if native_vlan.get('mode',None)!='route':                   # Look for routed native VLAN
      continue
    for j in list(node.interfaces):
      if j.get('parent_ifindex',None)!=i.ifindex:
        continue
      if j.get('vlan.mode','irb') in ['bridge','irb']:          # Are we dealing with a mixed trunk?
        report_quirk(
          f"You cannot use a mixed trunk with a routed native VLAN",
          more_data=[ f"node {node.name} interface {i.ifname} ({i.name}) vlan {i._vlan_native}" ],
          more_hints=[ "Use 'mode: irb' instead for the native VLAN" ],
          quirk='native_routed_on_mixed_trunk',
          category=log.IncorrectType,
          node=node)

"""
Checks whether this node uses OSPF passive interfaces inside a vrf. NVUE does not support these correctly, because the scripts
at /usr/lib/python3/dist-packages/nos/funits/cue_frr_v1/templates/frr_ospf_intf.conf.j2 use 'passive-interface' instead of
'ip ospf passive' at the interface level (which is VRF aware)
"""
def nvue_check_ospf_passive_in_vrf(node: Box) -> None:
  err_data = []
  for vrf,vdata in node.get('vrfs',{}).items():
    for i in vdata.get('ospf.interfaces',[]):
      if 'passive' in i.ospf and i.ospf.passive is True:
        err_data.append(f'Interface {i.ifname} inside VRF {i.vrf} using ospf.passive=True')
        i.ospf.passive = False

  if err_data:
    report_quirk(
      f'Node {node.name} uses passive OSPF interfaces inside a VRF, which NVUE does not support; auto-converted to False',
      quirk='vrf_ospf_passive',
      category=Warning,
      more_data=err_data,
      node=node)

"""
In case of multiple loopbacks, merges OSPF settings into 1 if compatible; else throws an error
"""
def nvue_merge_ospf_loopbacks(node: Box) -> None:
  err_data = []
  for i in node.get('interfaces',[]):
    if i.type!='loopback' or 'ospf' not in i:
      continue
    if 'ospf' in node.loopback:
      ospf_excl_passive = { k:v for k,v in i.ospf.items() if k!='passive' }
      if ospf_excl_passive == { k:v for k,v in node.loopback.ospf.items() if k!='passive' }:
        if i.ospf.get('passive',False) is False:
          node.loopback.ospf.passive = False
        i.pop('ospf',None)
        report_quirk(
          f'Node {node.name} uses a secondary loopback with OSPF { i.ifname }, merged with primary loopback',
          quirk='loopback_merge_ospf',
          category=Warning,
          node=node)
        continue
    err_data.append(f'Secondary loopback {i.ifname}')

  if err_data:
    report_quirk(
      f'Node {node.name} uses secondary loopback(s) with OSPF configuration that differs from the primary loopback',
      quirk='secondary_loopback_ospf',
      more_data=err_data,
      node=node)

"""
In case of loopbacks inside VRFs, checks that the OSPF attributes are consistent with the VRF
"""
def nvue_check_ospf_vrf_loopbacks(node: Box) -> None:
  err_data = []
  for vrf,vdata in node.get('vrfs',{}).items():
    if 'ospf' not in vdata:
      continue
    vrf_area = vdata.get('ospf.area',node.get('ospf.area','0.0.0.0'))
    for i in vdata.get('ospf.interfaces',[]):
      if i.type!='loopback':
        continue
      if 'area' in i.ospf and i.ospf.area != vrf_area:
        err_data.append(f'VRF {vrf} loopback with incompatible OSPF area {i.ospf.area} different from VRF area {vrf_area}')

  if err_data:
    report_quirk(
      f'Node {node.name} uses VRF loopback(s) with a different OSPF area, not supported',
      quirk='vrf_loopback_ospf_area',
      more_data=err_data,
      node=node)

"""
In case VXLAN is used in combination with mlag, require that the mlag.vtep plugin be enabled.
If not, the VXLAN anycast IP does not get provisioned, and the device fails to bringup the VXLAN interface
"""
def nvue_mlag_vxlan_require_plugin(node: Box, topology: Box) -> None:
  if not node.get('lag.mlag.peer'):
    return
  if 'mlag.vtep' in topology.get('plugin',[]):
    return
  report_quirk(
      f'Node {node.name} uses MLAG with VXLAN, which requires the mlag.vtep plugin to work',
      quirk='vxlan_mlag_vtep_plugin',
      more_data="Without this plugin, VXLAN interfaces will remain DOWN due to missing anycast IP",
      node=node)

def nvue_check_nssa_summarize(node: Box) -> None:
  for (odata,_,_) in _rp_utils.rp_data(node,'ospf'):
    if 'areas' not in odata:
      continue
    for area in odata.areas:
      if area.kind != 'nssa':
        continue
      if 'external_range' in area or 'external_filter' in area:
        report_quirk(
          f'{node.name} cannot summarize type-7 NSSA routes (area {area.area})',
          more_hints = [ 'Cumulus cannot configure NSSA type-7 ranges, FRR version too old' ],
          node=node,
          category=Warning,
          quirk='ospf_nssa_range')

class Cumulus_Nvue(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    # Cumulus.device_quirks(node,topology)
    mods = node.get('module',[])
    if 'ospf' in mods:
      if 'vrfs' in node:
        check_ospf_vrf_default(node)
        nvue_check_ospf_passive_in_vrf(node)
        nvue_check_ospf_vrf_loopbacks(node)
      nvue_check_ospfv3(node)
      nvue_check_nssa_summarize(node)
      nvue_merge_ospf_loopbacks(node)

    if 'stp' in mods:
      nvue_check_stp_features(node,topology)

    if 'vxlan' in mods and 'lag' in mods:
      nvue_mlag_vxlan_require_plugin(node,topology)

    if 'vlan' in mods:
      nvue_check_native_routed_on_mixed_trunk(node,topology)

    if devices.get_provider(node,topology) == 'clab':
      report_quirk(
        text=f"Cumulus VX 5.x container used for node {node.name} is not supported and might not work correctly",
        node=node,
        category=Warning,
        quirk="unsupported_container",
        more_hints=[ "See https://netlab.tools/caveats/#caveats-cumulus-nvue for more details "])
