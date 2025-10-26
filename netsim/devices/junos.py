#
# Juniper JunOS quirks
# # Every interface is a subunit ->
# # rename interface names from ge-0/0/0 to ge-0/0/0.0 (and so avoid using unit 0 on the initial template)
# # the same can apply to loopbacks, irbs, ...
# # + if the vlan module is in use, and multiple units are present, set the unit 0 as untagged vlan but with the vlan-id (default 1)
#
import copy

from box import Box

from ..utils import log, strings
from . import _Quirks, report_quirk

JUNOS_MTU_DEFAULT_HEADER_LENGTH = 14
JUNOS_MTU_FLEX_VLAN_HEADER_LENGTH = 22

# constants used in BGP Policies
JUNOS_POLICY_NHS = 'next-hop-{ next_hop_self }-{ af }'
JUNOS_POLICY_DEFAULT_ORIGINATE = 'bgp-default-route'
JUNOS_COMMON_BGP_POLICIES = [
  'bgp-advertise',
  'bgp-redistribute',
]
JUNOS_POLICY_LAST = 'bgp-final'
JUNOS_POLICY_IN_CLEANUP = 'bgp-initial'
JUNOS_POLICY_VRF_EXPORT = 'vrf-{}-bgp-export'

def _aspath_regex_convert(r: str) -> str:
  if r.startswith("^") or r.endswith("$") or r == '.*':
    # empty
    if r == '^$':
      return '()'
    # everything
    if r == '.*' or r == '^.*$':
      return '.*'
    if r.startswith("^") and not r.endswith("$"):
      r = r + " .*"
    if r.endswith("$") and not r.startswith("^"):
      r = ".* " + r
  # if we have no idea, or no regex, just return the same string
  return r

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
          # node flag required for creating policy
          node.bgp._junos_default_originate = True
          break

def policy_aspath_quirks(node: Box, topology: Box) -> None:
  if 'routing' not in node.get('module',[]):
    return
  for asp_name,asp_list in node.routing.get('aspath', {}).items():
    for asp_item in asp_list:
      aspath = asp_item.get('path', '.*')
      asp_item._junos_path = _aspath_regex_convert(aspath)

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

def community_set_quirk(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  if 'routing' not in mods or 'bgp' not in mods:
    return
  # JunOS policy, when setting/deleting a community, requires that the community itself is defined as 'policy-options community'
  # Let's fake out the communities required in "then" sets
  comm_name_prefix = "x_comm"
  # add routing.community struct if not present
  if not 'community' in node.routing:
    node.routing['community'] = {}
  for pl_name, pl_list in node.routing.get('policy', {}).items():
    for pl_item in pl_list:
      comm_struct = pl_item.get('set.community', {})
      if comm_struct:
        for ct in ['standard','extended','large']:
          for comm in comm_struct.get(ct, []):
            comm_action = 'set'
            if comm_struct.get('append', False):
              comm_action = 'add'
            if comm_struct.get('delete', False):
              comm_action = 'del'
            # add this "fake" community to the community list
            comm_list_name = f"{comm_name_prefix}_{comm_action}_{comm}"
            comm_list_name = comm_list_name.replace(':', '_')
            comm_list_name = comm_list_name.replace('.', '_')
            if log.debug_active('quirks'):
              print(f" - Found community set {comm} in policy {pl_name}, creating list {comm_list_name}")
            comm_list = [{ "action": "permit", "_value": comm }]
            # community set will overwrite the community used for flow control - let's add it here if needed
            if comm_action == 'set' and pl_item.get('action', 'permit') == 'permit':
              if ct == 'large':
                comm_list.append({ "action": "permit", "_value": "65535:0:65536" })
              else:
                comm_list.append({ "action": "permit", "_value": "large:65535:0:65536" })
            node.routing.community[comm_list_name] = {
              'type': ct,
              'value': comm_list,
            }

def _bgp_neigh_import_policy_chain_build(neigh: Box, node: Box, vrf_name: str) -> None:
  need_to_have_neigh_policy = False
  neigh_policy = []
  neigh_policy.append(JUNOS_POLICY_IN_CLEANUP)
  custom_policy = neigh.get('policy.in', '')
  if custom_policy:
    neigh_policy.append(custom_policy)
    need_to_have_neigh_policy = True
  neigh_policy.append(JUNOS_POLICY_LAST)
  if need_to_have_neigh_policy:
    # copy the object neigh_policy - (Assignment statements in Python do not copy objects)
    neigh._junos_policy['import'] = copy.deepcopy(neigh_policy)
  return

def _bgp_neigh_export_policy_chain_build(neigh: Box, default: list, vrf_name: str) -> None:
  need_to_have_neigh_policy = False
  neigh_policy = []
  if 'next_hop_self' in neigh:
    for af in log.AF_LIST:
      if af in neigh:
        policy_name = strings.eval_format(JUNOS_POLICY_NHS,neigh + { 'af': af })
        neigh_policy.append(policy_name)
        need_to_have_neigh_policy = True
  
  if vrf_name:
    neigh_policy.append(JUNOS_POLICY_VRF_EXPORT.format(vrf_name))
  else:
    neigh_policy.extend(JUNOS_COMMON_BGP_POLICIES)
  
  if neigh.get('default_originate', False):
    neigh_policy.append(JUNOS_POLICY_DEFAULT_ORIGINATE)
    need_to_have_neigh_policy = True
  custom_policy = neigh.get('policy.out', '')
  if custom_policy:
    neigh_policy.append(custom_policy)
    need_to_have_neigh_policy = True
  neigh_policy.append(JUNOS_POLICY_LAST)
  # define the data structure, if needed
  if need_to_have_neigh_policy and neigh_policy != default:
    neigh._junos_policy['export'] = neigh_policy

  return

def build_bgp_import_export_policy_chain(node: Box, topology: Box) -> None:
  # build per node/vrf and per-peer import and export policy chains, based on all the different
  #  modules and config (i.e., basic bgp, bgp.session, bgp.policy, routing)
  #  this is to avoid multiple templates to reference multiple times (with the risk of overwriting) the same policies
  #  (remember we use a local internal large community to control the polocy flow)
  # IMPORT Policy chain (for now this is useful only on specific neigh, no default policy)
  #  - drop internal flow community (for security purposes, we don't want external peers to control our flows)
  #  - vrf specific policy, if present (not for now)
  #  - custom policy (if neigh.policy.in - applies only to neigh) [{{ n.policy.in }}-{{ af }}]
  #  - default last resort policy
  # EXPORT Policy chain (needs to be improved for VRF)
  #  [default vrf]
  #  - next-hop-self (if ibgp and bgp.next_hop_self). 
  #      on global level, this must be applied only on the template, cannot discriminate here
  #  - bgp-advertise
  #  - bgp-redistribute
  #  - bgp-default-route (if neigh.default_originate true - only to neigh)
  #  - custom policy (if neigh.policy.out) [{{ n.policy.out }}-{{ af }}]
  #  - bgp-final
  #  [specific vrf]
  #  - next-hop-self (if ibgp and bgp.next_hop_self)
  #  - vrf-{{n}}-bgp-export --> to be improved
  #  - custom policy (if neigh.policy.out) [{{ n.policy.out }}-{{ af }}]
  #  - bgp-final
  mods = node.get('module',[])
  if 'bgp' not in mods:
    return
  ## policy list is a struct, which defines if a policy is per af or not (i.e., routing/bgp.policy uses {policy}-{af} for the names)
  # bgp for default routing table
  # - default policy to be applied at bgp/group level
  #  (multi steps to use constants)
  node.bgp._junos_policy.export = []
  node.bgp._junos_policy.ibgp = []
  if node.bgp.get('next_hop_self',False):
    for af in log.AF_LIST:
      if af not in node.af:
        continue
      policy_name = strings.eval_format(JUNOS_POLICY_NHS,{ 'next_hop_self': 'ebgp', 'af': af })
      node.bgp._junos_policy.ibgp.append(policy_name)

  node.bgp._junos_policy.export.extend(JUNOS_COMMON_BGP_POLICIES)
  node.bgp._junos_policy.export.append(JUNOS_POLICY_LAST)
  def_policy = node.bgp._junos_policy.ibgp + node.bgp._junos_policy.export
  # - per neighbor policies
  for ngb in node.get('bgp.neighbors',[]):
    # export policy
    _bgp_neigh_export_policy_chain_build(ngb, def_policy, '')
    # import policy
    _bgp_neigh_import_policy_chain_build(ngb, node, '')

  if 'vrf' not in mods:
    return
  # bgp for different VRFs
  for vname,vdata in node.vrfs.items():
    # common export policy chain for vrf
    vdata.bgp._junos_policy.export = [
      JUNOS_POLICY_VRF_EXPORT.format(vname),
      JUNOS_POLICY_LAST
    ]
    def_policy = vdata.bgp._junos_policy.export
    for ngb in vdata.get('bgp.neighbors', []):
      # export policy
      _bgp_neigh_export_policy_chain_build(ngb, def_policy, vname)
      # import policy
      _bgp_neigh_import_policy_chain_build(ngb, node, vname)

  return

class JUNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if log.debug_active('quirks'):
      print(f"*** DEVICE QUIRKS FOR JUNOS {node.name}")
    fix_unit_0(node,topology)
    check_multiple_loopbacks(node,topology)
    check_evpn_ebgp(node,topology)
    policy_aspath_quirks(node,topology)
    as_prepend_quirk(node,topology)
    community_set_quirk(node,topology)
    default_originate_check(node,topology)
    build_bgp_import_export_policy_chain(node,topology)
