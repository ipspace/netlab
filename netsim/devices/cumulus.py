#
# Arista EOS quirks
#
from box import Box

from . import _Quirks, report_quirk
from ..utils import log
from ..augment import devices

def check_ospf_vrf_default(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if vdata.get('ospf.default',None):
      log.error(
        f"VRF OSPF default route is not working on Cumulus Linux (node {node.name}, vrf {vname})",
        category=log.IncorrectType,
        module='quirks')

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
  
  if err_data:
    report_quirk(
      f'node {node.name} does not support STP port_priority on non-VLAN interfaces or without PVRST ({stp_protocol})',
      quirk='stp_port_priority',
      more_data=err_data,
      node=node)

class Cumulus(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'ospf' in mods and 'vrfs' in node:
      check_ospf_vrf_default(node)
    
    # NVUE specific quirks
    if node.device == "cumulus_nvue":
      if 'stp' in mods:
        nvue_check_stp_features(node,topology)
