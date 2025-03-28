#
# Juniper JunOS quirks
# # Every interface is a subunit ->
# # rename interface names from ge-0/0/0 to ge-0/0/0.0 (and so avoid using unit 0 on the initial template)
# # the same can apply to loopbacks, irbs, ...
# # + if the vlan module is in use, and multiple units are present, set the unit 0 as untagged vlan but with the vlan-id (default 1)
#
from box import Box

from . import _Quirks,report_quirk
from ..utils import log
from ..augment import devices

JUNOS_MTU_DEFAULT_HEADER_LENGTH = 14
JUNOS_MTU_FLEX_VLAN_HEADER_LENGTH = 22

def unit_0_trick(intf: Box, round: str ='global') -> None:
  oldname = intf.ifname
  newname = oldname + ".0"
  if log.debug_active('quirks'):
    print(f" - [{round}] Found interface {intf.ifname}, renaming to {newname}")
  intf.ifname = newname
  intf.junos_interface = oldname
  intf.junos_unit = '0'

def set_junos_mtu(intf: Box, delta: int) -> None:
  if 'mtu' in intf:
    mtu = int(intf.mtu)
    intf._junos_mtu_with_headers = mtu + delta

def fix_unit_0(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  # Need to understand if I need to configure unit 0 or not.
  base_vlan_interfaces = []

  for intf in node.get('interfaces', []):
    if not '.' in intf.ifname:
        unit_0_trick(intf)
        set_junos_mtu(intf, JUNOS_MTU_DEFAULT_HEADER_LENGTH)
        if 'vlan' in mods:
          # check VLAN params, and add if needed
          if '_vlan_native' in intf:
            # get native ID
            intf._vlan_native_id = node.vlans[intf._vlan_native].id

    if '.' in intf.ifname and intf.ifname != 'irb':
      # get basic interface, and add to list.
      ifname_split = intf.ifname.split('.')
      intf.junos_interface = ifname_split[0]
      intf.junos_unit = ifname_split[1]
      if 'vlan' in mods and 'vlan' in intf:
        base_vlan_interfaces.append(ifname_split[0])

  # add additional vlan parameters.
  if len(base_vlan_interfaces) > 0:
    for intf in node.get('interfaces', []):
      if intf.junos_unit=='0' and intf.junos_interface in base_vlan_interfaces:
        intf._vlan_master = True
        # define vlan mtu override for VLAN tagging
        junos_vlan_kind = topology.defaults.devices[node.device].features.vlan.get('model', '')
        # in case of "flexible vlan tagging", 22 bytes more, depending on link type
        if junos_vlan_kind == 'router':
          # for a router, always add it
          set_junos_mtu(intf, JUNOS_MTU_FLEX_VLAN_HEADER_LENGTH)
        elif junos_vlan_kind == 'l3-switch':
          # for a l3-switch, add it on vlan mode route or if no vlan structure is defined (flex vlan tagging with native only)
          if 'vlan' not in intf or intf.get('vlan.mode',None) == 'route':
            set_junos_mtu(intf, JUNOS_MTU_FLEX_VLAN_HEADER_LENGTH)
  
  # need to append .0 unit trick to the interface list copied into vrf->ospf
  if 'vrf' in mods and 'ospf' in mods:
    for vname,vdata in node.vrfs.items():
      for intf in vdata.get('ospf.interfaces',[]):
        if not '.' in intf.ifname:
          unit_0_trick(intf, f"vrf({vname})/ospf")

def check_multiple_loopbacks(node: Box, topology: Box) -> None:
  vrf_count: dict = {}
  if 'loopback' in node:
    vrf_count['default'] = 1

  for intf in node.interfaces:
    if intf.get('type','') != 'loopback':
      continue

    vrf = intf.get('vrf','default')
    if vrf in vrf_count:
      vrf_count[vrf] += 1
    else:
      vrf_count[vrf] = 1

  for vname,vcnt in vrf_count.items():
    if vcnt <= 1:
      continue
    report_quirk(
      text=f'Node {node.name} (device {node.device}) has {vcnt} loopbacks in vrf {vname}',
      node=node,
      category=log.IncorrectValue,
      quirk='multi_loopback',
      hint='single_lb',
      module='junos')

def check_evpn_ebgp(node: Box, topology: Box) -> None:
  for ngb in node.get('bgp.neighbors',[]):
    if ngb.type == 'ebgp' and ngb.get('evpn',False):
      ngb_activate = ngb.get('activate', {})
      if ngb_activate.get('ipv4', False) or ngb_activate.get('ipv6', False):
        report_quirk(
          f'EVPN is not supported on EBGP sessions together with other address families (node {node.name} neighbor {ngb.name})',
          node=node,
          category=log.IncorrectType,
          quirk='evpn_ebgp')

class JUNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print(f"*** DEVICE QUIRKS FOR JUNOS {node.name}")
    fix_unit_0(node,topology)
    check_multiple_loopbacks(node,topology)
    check_evpn_ebgp(node,topology)
