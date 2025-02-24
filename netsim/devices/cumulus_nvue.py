#
# Cumulus NVUE quirks
#
from box import Box

from . import _Quirks, report_quirk
# from .cumulus import Cumulus  # This causes Cumulus_Nvue to get skipped
from .cumulus import check_ospf_vrf_default
from ..utils import log
from ..augment import devices
from .. import data
import netaddr

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
    log.error(f"Node '{node.name}' uses OSPFv3 which cannot be configured through Cumulus NVUE; use a regular 'cumulus' node instead",
      category=log.FatalError,
      module='ospf',
      hint='ospfv3')

"""
Checks for mixed trunk interfaces with native vlan, and creates a separate subinterface (vlan_member) for the native VLAN.
This is needed because the parent interface gets added to the VLAN-aware bridge, with the native vlan set as 'untagged'
"""
def nvue_create_native_subifs(node: Box, topology: Box) -> None:
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
        native_subif = data.get_empty_box()
        native_subif.ifname = f'{i.ifname}.{ native_vlan.id }'
        native_subif.name = f'[SubIf native VLAN {i._vlan_native}] ' + i.name
        native_subif.parent_ifindex = i.ifindex
        native_subif.parent_ifname = i.ifname
        native_subif.type = "vlan_member"
        native_subif.virtual_interface = True
        native_subif.ifindex = len(node.interfaces) + 1
        native_subif.vlan.name = i._vlan_native
        native_subif.vlan.access_id = native_vlan.id
        native_subif.vlan.mode = 'route'

        skip = [ 'bridge_group','subif_index','linkindex' ] + list(native_subif.keys())
        for att,value in { k:v for k,v in i.items() if k not in skip }.items():
          native_subif[att] = value
          i.pop(att,None)

        node.interfaces.append(native_subif)
        i.subif_index = i.subif_index + 1
        report_quirk(
          f'Node {node.name} uses a mixed trunk with a routed native VLAN; created sub-interface for native VLAN {native_vlan.id}',
          quirk='native_subif_on_mixed_trunk',
          category=Warning,
          node=node)
        break

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
    if 'ospf' in node.loopback and 'vrf' not in i:
      if i.ospf == node.loopback.ospf or (i.ospf == node.loopback.ospf+{'passive': False}):
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
      f'Node {node.name} uses secondary loopback(s) with OSPF configuration that differs from the primary loopback, or is in a VRF',
      quirk='secondary_loopback_ospf',
      more_data=err_data,
      node=node)

"""
In case of shared MLAG VTEP, marks the VTEP such that the correct configuration can be applied
"""
def mark_shared_mlag_vtep(node: Box, topology: Box) -> None:
  local_vtep = node.get('vxlan.vtep',None)
  if not local_vtep:
    return
  for n in topology.nodes.values():
    if n!=node and n.get('vxlan.vtep',None)==local_vtep:
      node.vxlan._shared_vtep = n.name
      return

class Cumulus_Nvue(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    # Cumulus.device_quirks(node,topology)
    mods = node.get('module',[])
    if 'ospf' in mods:
      if 'vrfs' in node:
        check_ospf_vrf_default(node)
        nvue_check_ospf_passive_in_vrf(node)
      nvue_check_ospfv3(node)
      nvue_merge_ospf_loopbacks(node)

    if 'stp' in mods:
      nvue_check_stp_features(node,topology)

    if 'vxlan' in mods:
      mark_shared_mlag_vtep(node,topology)
    nvue_create_native_subifs(node,topology)

    if devices.get_provider(node,topology) == 'clab':
      log.error(
        f"Cumulus VX 5.x container used for node {node.name} is not supported and might not work correctly",
        category=Warning,
        module='cumulus_nvue',
        more_hints=[ "See https://netlab.tools/caveats/#caveats-cumulus-nvue for more details "])
