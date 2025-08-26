#
# Nokia SR OS quirks
#

from box import Box

from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk


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
  if node.get('mpls.vpn',None):
    return

  for vname,vdata in node.get('vrfs',{}).items():
    if '_leaked_routes' in vdata and not vdata.get('evpn'):
      report_quirk(
        text=f'Inter-VRF route leaking on SR/OS is implemented only with MPLS/VPN or EVPN (node {node.name} vrf {vname})',
        node=node,
        category=log.IncorrectValue)

"""
Obsolete: this function tested whether we use 'allowas-in' with EVPN. It turned out to be FRR 10.3.1 gotcha;
the tests work like a charm with 10.2.2.
"""
def evpn_allowas_in(node: Box) -> None:
  for ngb in node.get('bgp.neighbors',[]):
    if not ngb.get('evpn',None):
      continue
    if not ngb.get('allowas_in',None):
      continue
    report_quirk(
      text=f'node {node.name}: cannot use "allowas_in" on BGP neighbor {node.name} with EVPN address family',
      more_hints = f'It looks SR/OS does not apply AS-path loop detection parameters to EVPN AF',
      quirk='evpn_allowas_in',
      node=node,
      category=log.IncorrectValue)

def set_port_mode(intf: Box, mode: str) -> None:
  if '_port_mode' not in intf:
    intf._port_mode = mode
  elif intf._port_mode != mode:
    intf._port_mode = 'hybrid'

def set_port_modes(node: Box) -> None:
  for intf in node.interfaces:
    if intf.type in ['svi', 'loopback']:
      continue

    t_intf = intf
    if intf.type == 'vlan_member':
      pif_list = [ p_if for p_if in node.interfaces if p_if.ifname == intf.parent_ifname ]
      if not pif_list:
        log.fatal(f'SROS: Cannot find parent interface {intf.parent_ifname} on node {node.name}')
      t_intf = pif_list[0]

    if 'vrf' in intf:
      set_port_mode(t_intf,'access')
    elif 'ipv4' in intf or 'ipv6' in intf:
      set_port_mode(t_intf,'network')
    else:
      set_port_mode(t_intf,'access')

"""
Configuring non-system VTEP on SR-OS is too much trouble. Let's check if the VTEP is equal to loopback IPv4
"""
def vxlan_vtep(node: Box) -> None:
  vtep = node.get('vxlan.vtep',None)
  if not vtep:
    return
  lbip = node.get('loopback.ipv4','x/x').split('/')[0]
  if vtep != lbip:
    report_quirk(
      text=f'Node {node.name} must use loopback IPv4 address as the VXLAN VTEP',
      more_hints = [ 'SR/OS supports non-system VTEP, but it was too much hassle to configure it' ],
      quirk='vxlan_vtep',
      node=node,
      category=log.IncorrectValue)

def adjust_system_ipv6_prefix(node: Box) -> None:
  v6lb = node.get('loopback.ipv6',None)
  if not v6lb:
    return

  (v6ad,v6pf) = v6lb.split('/')
  if v6pf != '128':
    node.loopback.ipv6 = f'{v6ad}/128'
    report_quirk(
      text=f'Loopback prefix {v6lb} on node {node.name} was changed to {node.loopback.ipv6}',
      more_hints=[ f'The IPv6 prefix configured on SR OS system (loopback) interface must be a /128' ],
      quirk='loopback_ipv6',
      node=node,
      category=Warning)

class SROS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    adjust_system_ipv6_prefix(node)
    set_port_modes(node)
    ipv4_unnumbered(node)
    vrf_route_leaking(node)
    vxlan_vtep(node)
  
  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.grpc',version='1.0.2')
