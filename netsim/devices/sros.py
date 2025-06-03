#
# Nokia SR OS quirks
#
from box import Box

from . import _Quirks,need_ansible_collection,report_quirk
from ..utils import log,routing as _routing
import re

def ipv4_unnumbered(node: Box) -> None:
  for intf in node.interfaces:
    if intf.get('ipv4',False) is not True:
      continue
    if isinstance(intf.get('ipv6',False),str):
      report_quirk(
        text=f'SR/OS cannot combine IPv6 GUA with IPv4 unnumbered (node {node.name} interface {intf.ifname})',
        node=node,
        category=log.IncorrectValue)

def vrf_route_leaking(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if '_leaked_routes' in vdata:
      report_quirk(
        text=f'We did not implement inter-VRF route leaking on SR/OS (node {node.name} vrf {vname})',
        node=node,
        category=log.IncorrectValue)

def evpn_vrf_rp(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if not vdata.get('evpn',None):
      continue
    if vdata.get('bgp.neighbors',[]) or vdata.get('ospf'):
      report_quirk(
        text=f'We did not implement propagation of EVPN ip-prefix routes into VRF routing protocols',
        more_data = f'Node {node.name} vrf {vname}',
        quirk='evpn_rp',
        node=node,
        category=log.IncorrectValue)

class SROS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    ipv4_unnumbered(node)
    vrf_route_leaking(node)
    evpn_vrf_rp(node)
  
  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.grpc',version='1.0.2')
