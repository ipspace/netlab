#
# CapeOS Bolt quirks
#
from box import Box

from ..utils import routing as _rp_utils
from . import _Quirks, report_quirk


def check_bgp_rr(node: Box) -> None:
  if node.get('bgp.rr',False):
    report_quirk(
      f'CapeOS Bolt cannot be a BGP route reflector (node {node.name})',
      node,
      quirk='bgp.rr')

def check_vrf_leaking(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if set(vdata.get('import',[])) - set(vdata.get('export',[])):
      report_quirk(
        f'CapeOS Bolt cannot leak routes between VRFs (node {node.name}, VRF {vname})',
        node,
        quirk='vrf.leaking')

def check_dhcp_client_default(node: Box) -> None:
  for intf in node.interfaces:
    if intf.get('dhcp.client.ipv4',False) and intf.get('dhcp.client.default',True) is False:
      report_quirk(
        f'CapeOS Bolt always installs the default route received from a DHCP server ' +\
        f'(node {node.name}, interface {intf.ifname})',
        node,
        quirk='dhcp.client_default')

def check_ospf_parameters(node: Box) -> None:
  for (odata,_,vname) in _rp_utils.rp_data(node,'ospf'):
    o_name = f'VRF {vname} on node {node.name}' if vname else f'node {node.name}'
    if any(kw in odata.get('default',{}) for kw in ('cost','type')):
      report_quirk(
        f'CapeOS Bolt cannot set the cost or type of the OSPF default route ({o_name})',
        node,
        quirk='ospf.default')
    for area in odata.get('areas',[]):
      if any('cost' in rng for rng in area.get('range',[])):
        report_quirk(
          f'CapeOS Bolt cannot set the cost of OSPF area ranges ({o_name}, area {area.area})',
          node,
          quirk='ospf.range_cost')
      if area.get('kind','') == 'nssa' and area.get('default.cost',None):
        report_quirk(
          f'CapeOS Bolt cannot set the cost of the NSSA default route ({o_name}, area {area.area})',
          node,
          quirk='ospf.nssa_cost')

class CapeOSBolt(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'bgp' in mods:
      check_bgp_rr(node)
    if 'vrf' in mods:
      check_vrf_leaking(node)
    if 'dhcp' in mods:
      check_dhcp_client_default(node)
    if 'ospf' in mods:
      check_ospf_parameters(node)
