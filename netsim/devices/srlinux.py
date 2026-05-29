#
# SR Linux quirks
# # 
# # inter-VRF route leaking is only supported in combination with BGP EVPN
# # based on IP prefixes, not (currently 24.3.1) on communities
#
import re

from box import Box

from ..augment import devices as a_devices
from ..utils import log
from ..utils import routing as _routing
from . import _Quirks, need_ansible_collection, report_quirk

CLAB_DEFAULT_TYPE = 'ixr-d2'


def check_prefix_deny(node: Box) -> None:
  """Report a quirk when prefix filters use a deny action (unsupported on SR Linux)."""
  for pf_name,pf_list in node.get('routing.prefix',{}).items():
    for p_entry in pf_list:
      if p_entry.get('action',None) == 'deny':
        report_quirk(
          text=(
            f'SR Linux does not support "deny" action in prefix filters '
            f'(node {node.name} prefix filter {pf_name})'
          ),
          node=node,
          quirk='prefix_deny',
          category=log.IncorrectValue)
        break

def cleanup_neighbor_transport(node: Box, topology: Box) -> None:
  """Remove unused BGP transport addresses when no address family is activated."""
  for ngb in _routing.neighbors(node,vrf=True):
    if 'local_if' in ngb:               # True unnumbered, move on
      continue
    ipv4 = ngb.get('ipv4',None)
    if ipv4 is True:                    # Could be RFC 8950 over numbered IPv6, move on
      continue

    # Remove IPv6 transport session if IPv6 is not activated
    for af in ['ipv4','ipv6']:
      if af not in ngb:                 # Do we have the neighbor IP address in this address family?
        continue
      if not isinstance(ngb[af],str):   # Is it a string (real IP address)?
        continue
      if ngb.activate.get(af,False):    # Is the AF activated?
        continue

      if af == 'ipv4':
        x_af = [ af for af in ['evpn','vpnv4','vpnv6','6pe'] if af in ngb ]
        if x_af:                        # Do we have extra address families running over IPv4 transport?
          continue

      report_quirk(
        text=f'Removed {af} transport address {ngb[af]} for BGP neighbor {ngb.name} on node {node.name}',
        more_hints=['No BGP address family was activated for this BGP neighbor'],
        quirk='bgp_transport',
        node=node,
        category=Warning)
      ngb.pop(af)

def set_api_version(node: Box) -> None:
  """Set node._srl_version from the container image tag."""
  version = re.search(r'^.*/srlinux:([\d]+.[\d]+).*$', node.box)
  node._srl_version = [ 25, 3 ]         # Assume 25.3 release
  if version is not None:               # If we managed to match the SR Linux image name
    try:                                # ... try to extract release info into a list of ints
      node._srl_version = [ int(v) for v in version.group(1).split('.') ]
    except:                             # Extraction process failed?
      pass                              # ... no worries, we'll use the default

def check_nssa_default_cost(node: Box) -> None:
  """Warn when OSPF NSSA areas specify a default-metric (not supported on SR Linux)."""
  for (odata,_,_) in _routing.rp_data(node,'ospf'):
    if 'areas' not in odata:
      continue
    for area in odata.areas:
      if area.kind != 'nssa':
        continue
      cost = area.get('default.cost')
      if cost:
        report_quirk(
          f'{node.name} cannot apply a default cost ({cost}) to NSSA area {area.area}',
          more_hints = [ 'Nokia SR Linux cannot configure a default-metric for NSSA areas' ],
          node=node,
          category=Warning,
          quirk='ospf_nssa_default_cost')

def normalize_interface_descriptions(node: Box) -> None:
  """Normalize interface descriptions (-> to ~, remove square brackets)."""

  # Normalize regular interface descriptions
  for intf in node.get('interfaces',[]):
    if intf.get('name'):
      intf.name = intf.name.replace('->','~').replace('[','').replace(']','')

def hyphenate_legacy_clab_type(dt: str, clab_types: Box) -> str:
  """Convert undashed legacy clab.type to canonical form (1 or 2 hyphen insertions)."""

  for name in clab_types.keys():
    if name.replace('-', '') == dt:
      return name

  return "unknown"

def normalize_clab_type(node: Box, topology: Box) -> str:
  """Validate clab.type and map legacy undashed names to hyphenated containerlab values."""
  dt = node.get('clab.type', CLAB_DEFAULT_TYPE)
  if a_devices.get_provider(node, topology.defaults) != 'clab':
    return dt

  clab_types = a_devices.get_device_attribute(node, 'clab_types', topology.defaults)
  if not isinstance(clab_types, Box):
    return dt

  original = dt
  if '-' not in dt:
    dt = hyphenate_legacy_clab_type(dt, clab_types)

  if dt in clab_types:
    if dt != original:
      report_quirk(
        text=f'Normalized legacy clab.type "{original}" to "{dt}" on node {node.name}',
        more_hints=['Use hyphenated containerlab type names (for example ixr-6e instead of ixr6e)'],
        node=node,
        quirk='clab_type_legacy',
        category=Warning)
      node.clab.type = dt
    return dt

  report_quirk(
    text=f'Invalid clab.type "{original}" on node {node.name}',
    more_hints=[
      'Use a documented SR Linux hardware type (see https://containerlab.dev/manual/kinds/srl/#types)',
      f'Valid types: {", ".join(clab_types.keys())}',
    ],
    node=node,
    quirk='clab_type',
    category=log.IncorrectValue)
  return "invalid"

def license_needed(dt: str, features: Box) -> bool:
  """Return True when the emulated platform requires an SR Linux license for MPLS/SR."""
  p_list = features.get('mpls._platforms',[])
  for p_prefix in p_list:
    if dt.startswith(p_prefix):
      return True

  return False

ETH_FRAME_MTU_OVERHEAD = 14
SRL_MAX_FRAME_MTU_7220 = 9398   # 7220 IXR (ixr-d*, ixr-h*)
SRL_MAX_FRAME_MTU_7250 = 9486   # 7250 IXR and 7730 SXR (ixr-6*, ixr-10*, ixr-18*, ixr-x*, sxr-*)

def max_frame_mtu_for_type(clab_type: str) -> int | None:
  """Return the maximum L2 frame size for a containerlab hardware type, if known."""
  if clab_type.startswith(('ixr-d', 'ixr-h')):
    return SRL_MAX_FRAME_MTU_7220
  if clab_type.startswith(('ixr-6', 'ixr-10', 'ixr-18', 'ixr-x', 'sxr-')):
    return SRL_MAX_FRAME_MTU_7250
  return None

def check_mtu(node: Box, clab_type: str) -> None:
  """Report a quirk when node MTU exceeds the limit for the emulated hardware platform."""
  mtu = node.get('mtu', None)
  if mtu is None:
    return

  max_frame = max_frame_mtu_for_type(clab_type)
  if max_frame is None:
    return

  if mtu + ETH_FRAME_MTU_OVERHEAD > max_frame:
    report_quirk(
      text=f'IP MTU {mtu} too large for given hardware platform: {clab_type}',
      node=node,
      quirk='mtu_too_large',
      category=log.IncorrectValue)

class SRLINUX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    dt = normalize_clab_type(node, topology)
    set_api_version(node)
    features = a_devices.get_device_features(node,topology.defaults)
    normalize_interface_descriptions(node)
    check_mtu(node,dt)
    is_licensed = False
    if license_needed(dt,features):
      if not node.clab.get('license',None):
        report_quirk(
          text=f'You need a valid SR Linux license to run {dt} container on node {node.name}',
          node=node,
          quirk='platform_license',
          category=log.MissingValue)
      else:
        is_licensed = True

    mods = node.get('module',[])
    if 'vrf' in mods and 'evpn' not in mods:
      vlist = []
      for vname,vrf in node.get('vrfs', {}).items():
        if len(vrf['import']) > 1 or len(vrf['export']) > 1:
          vlist.append(vname)

      if vlist:
        report_quirk(
          text='Inter-VRF route leaking is supported only in combination with BGP EVPN',
          more_data=[ f'Node {node.name} VRF(s) {",".join(vlist)}' ],
          node=node,
          quirk='vrf_route_leaking',
          category=log.IncorrectType)

    if 'bgp' in mods:
      cleanup_neighbor_transport(node,topology)
      if node._srl_version < [ 25, 3 ]:
        for c,vals in topology.get('bgp.community',[]).items():
          if 'extended' not in vals:
            report_quirk(
              text=(
                f'SR Linux on ({node.name}) before version 25.3.1 does not support '
                'filtering out extended communities for BGP.'
              ),
              more_data= [ f'{c}:{vals}' ],
              node=node,
              category=Warning,
              quirk='bgp_community')

    if ('mpls' in mods or 'sr' in mods) and not is_licensed:
      report_quirk(
         text=f'MPLS works only on (emulated) 7250-IXR and 7730-SXR routers (node {node.name})',
         more_hints=['Set node clab.type to a different device model (see https://containerlab.dev/manual/kinds/srl/)'],
         node=node,
         category=log.IncorrectValue)

    if 'routing' in mods and node.get('routing.prefix',None):
      check_prefix_deny(node)

    if 'ospf' in mods:
      check_nssa_default_cost(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.srlinux',version='0.5.0')
