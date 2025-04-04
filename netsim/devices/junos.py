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

def default_originate_check(node: Box, topology: Box) -> None:
  # If BGP is enabled, and there is at least one peer with default-originate, then we need to create the default route discard
  if 'bgp' not in node.get('module',[]):
    return
  for ngb in node.get('bgp.neighbors',[]):
    if ngb.get('default_originate', False):
      node.bgp._junos_default_originate = True
      break
  if 'vrf' in node.get('module',[]):
    for vname,vdata in node.vrfs.items():
      for ngb in vdata.get('bgp.neighbors', []):
        if ngb.get('default_originate', False):
          vdata.bgp._junos_default_originate = True
          break

def check_routing_policy_quirks(node: Box, topology: Box) -> None:
  if 'routing' not in node.get('module',[]):
    return
  # prefix-list cannot directly use ge/le
  for pl_name, pl_list in node.routing.get('prefix', {}).items():
    for pl_item in pl_list:
      if 'min' in pl_item or 'max' in pl_item:
        report_quirk(
          f'JunOS prefix-list items cannot have min/max items (node {node.name} prefix-list {pl_name})',
          node=node,
          category=log.IncorrectValue,
          quirk='routing_prefixlist_min_max',
          module='junos'
        )
  # AS-PATH cannot directly have action "deny"
  for asp_name,asp_list in node.routing.get('aspath', {}).items():
    for asp_item in asp_list:
      if asp_item.get('action', '') == 'deny':
        report_quirk(
          f'JunOS as-path items cannot have deny items (node {node.name} as-path {asp_name})',
          node=node,
          category=log.IncorrectValue,
          quirk='routing_aspath_deny',
          module='junos'
        )
  # Community match cannot directly have action "deny"
  for c_name,c_list in node.routing.get('community', {}).items():
    for c_item in c_list.value:
      if c_item.get('action', '') == 'deny':
        report_quirk(
          f'JunOS community match cannot have deny items (node {node.name} community {c_name})',
          node=node,
          category=log.IncorrectValue,
          quirk='routing_community_deny',
          module='junos'
        )

def as_prepend_quirk(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  if 'routing' not in mods or 'bgp' not in mods:
    return
  # https://github.com/ipspace/netlab/issues/2113
  # When prepending an AS number different than the local one, JunOS put the prepend as ath the beginning of the AS_PATH 
  # (while other vendors perform the prepending first, and then add its own AS at the beginning).
  # This leads other BGP peers to deny an update received from an eBGP peer that does not list its autonomous system number at the beginning of the AS_PATH.
  # For this reason, in case we detect a prepend which does not start with the local-as, we add it at the beginning of the AS_PATH
  local_as = str(node.bgp['as']) ## cannot use node.bgp.as - 'as' is reserved keyword
  for pl_name, pl_list in node.routing.get('policy', {}).items():
    for pl_item in pl_list:
      if pl_item.get('set.prepend.path', ''):
        current_path = pl_item.set.prepend.path
        # convert to list
        path_items = current_path.split(' ')
        if len(path_items) > 0 and path_items[0] != local_as:
          path_items.insert(0, local_as)
          new_path = " ".join(path_items)
          report_quirk(
            f'JunOS as-path-prepend with AS different from local one requires adding the local AS at the beginning of the AS_PATH - Adding it. (node {node.name} policy {pl_name} current as-path "{current_path}" new as-path "{new_path}")',
            node=node,
            category=Warning,
            quirk='routing_as_prepend_nonlocal_as',
            module='junos'
          )
          pl_item.set.prepend.path = new_path

class JUNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print(f"*** DEVICE QUIRKS FOR JUNOS {node.name}")
    fix_unit_0(node,topology)
    check_multiple_loopbacks(node,topology)
    check_evpn_ebgp(node,topology)
    check_routing_policy_quirks(node,topology)
    as_prepend_quirk(node,topology)
    default_originate_check(node,topology)
