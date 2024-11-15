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

class Cumulus_Nvue(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    # Cumulus.device_quirks(node,topology)
    mods = node.get('module',[])
    if 'ospf' in mods and 'vrfs' in node:
      check_ospf_vrf_default(node)

    # NVUE specific quirks
    if 'stp' in mods:
      nvue_check_stp_features(node,topology)
