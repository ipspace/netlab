#
# Cumulus NVUE quirks
#
from box import Box

from . import _Quirks, report_quirk
# from .cumulus import Cumulus  # This causes Cumulus_Nvue to get skipped
from .cumulus import check_ospf_vrf_default
from ..utils import log
from ..augment import devices

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
Checks for vrf route leaking usage which is not yet implemented
"""
def nvue_check_vrf_route_leaking(node: Box) -> None:
  for vname,vdata in node.get("vrfs",{}).items():
    if len(vdata.get('export',[]))>1 or len(vdata.get('import',[]))>1:
      log.error(f"Topology uses vrf route leaking which Netlab does not implement (yet) for Cumulus NVUE node '{node.name}'",
        category=log.FatalError,
        module='vrf',
        hint='route leaking')
      return

"""
Checks for OSPFv3 which is not supported by NVUE configuration command
"""
def nvue_check_ospfv3(node: Box) -> None:
  if node.get('ospf.af.ipv6',False):
    log.error(f"Node '{node.name}' uses OSPFv3 which cannot be configured through Cumulus NVUE; use a regular 'cumulus' node instead",
      category=log.FatalError,
      module='ospf',
      hint='ospfv3')

class Cumulus_Nvue(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    # Cumulus.device_quirks(node,topology)
    mods = node.get('module',[])
    if 'ospf' in mods:
      if 'vrfs' in node:
        check_ospf_vrf_default(node)
      nvue_check_ospfv3(node)

    # NVUE specific quirks
    if 'stp' in mods:
      nvue_check_stp_features(node,topology)
    
    if 'vrf' in mods:
      nvue_check_vrf_route_leaking(node)

    if devices.get_provider(node,topology) == 'clab':
      log.error(
        f"Cumulus VX 5.x container used for node {node.name} is not supported and might not work correctly",
        category=Warning,
        module='cumulus_nvue',
        more_hints=[ "See https://netlab.tools/caveats/#caveats-cumulus-nvue for more details "])
