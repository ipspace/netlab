import typing

from . import _Module,_routing,_dataplane
from box import Box
from .. import common
from .. import data
from ..augment import devices

# Supported transports, in order of preference/default
SUPPORTED_TRANSPORTS = [ 'vxlan', 'mpls' ]

def enable_evpn_af(node: Box, topology: Box) -> None:
  bgp_session = data.get_from_box(node,'evpn.session') or []

  # Enable EVPN AF on all BGP neighbors with the correct session type
  # that also use EVPN module
  #
  for bn in node.bgp.get('neighbors',[]):
    if bn.type in bgp_session and 'evpn' in topology.nodes[bn.name].get('module'):
      bn.evpn = True

#
# Check EVPN-enabled VLANs
#
def node_vlan_check(node: Box, topology: Box) -> bool:
  if not node.evpn.vlans:            # Create a default list of VLANs if needed
    node.evpn.vlans = [ name for name,value in node.vlans.items() if 'evpn' in value or 'vni' in value ]

  OK = True
  vlan_list = []
  for vname in node.evpn.vlans:
    #
    # Report error for unknown VLAN names in VLAN list (they are not defined globally or on the node)
    if not vname in node.vlans and not vname in topology.get('vlans',{}):
      common.error(
        f'Unknown VLAN {vname} is specified in the list of EVPN-enabled VLANs in node {node.name}',
        common.IncorrectValue,'evpn')
      OK = False
      continue
    #
    # Skip VLAN names that are valid but not used on this node
    if not vname in node.vlans:
      continue

    # Normalize vlans by adding EVPN if not already, convert None to dict
    if not node.vlans[vname].evpn:
      node.vlans[vname].evpn = {}
    vlan_list.append(vname)

  node.evpn.vlans = vlan_list
  return OK

"""
Set EVPN transport parameter for (bundled) VLAN, validate supported values
"""
def set_transport(obj: Box, node: Box) -> None:
  # Don't use mpls transport if user only defined vxlan.vlans
  enabled = [m for m in node.get('module',[]) if m in SUPPORTED_TRANSPORTS and
             (data.get_from_box(node,f"{m}.vlans") or data.get_from_box(node,"evpn.vlans")) ]
  if not 'transport' in obj:
    for t in SUPPORTED_TRANSPORTS:
      if t in enabled:
        obj.transport = t
        return
    common.error(
      f'No supported EVPN transports ({SUPPORTED_TRANSPORTS}) enabled on node {node.name}: {enabled}',
      common.MissingValue,'evpn')
  elif obj.transport not in SUPPORTED_TRANSPORTS:
    common.error(
      f'Unsuppported EVPN transport {obj.transport} on node {node.name}',
      common.IncorrectValue,'evpn')
  elif obj.transport not in enabled:
    common.error(
      f'EVPN transport module {obj.transport} not enabled on node {node.name}',
      common.MissingValue,'evpn')

def vlan_based_service(vlan: Box, vname: str, node: Box, topology: Box) -> None:
  if not vlan.evpn:
    vlan.evpn = {}
  evpn  = vlan.evpn
  epath = f'nodes.{node.name}.vlans.{vname}.evpn'
  evpn.evi = evpn.evi or vlan.id                                    # Default EVI value: VLAN ID
  data.must_be_int(
    evpn,'evi',epath,
    module='evpn',
    min_value=1,max_value=65535)                                    # Check EVI data type in range
  if not 'rd' in evpn:                                              # Default RD value
    evpn.rd = f'{node.bgp.router_id}:{vlan.id}'
  for rt in ('import','export'):                                    # Default RT value
    if not rt in evpn:                                              # ... BGP ASN:vlan ID
      evpn[rt] = [ f"{node.bgp['as']}:{vlan.id}" ]
  set_transport(evpn,node)

def vlan_aware_bundle_service(vlan: Box, vname: str, node: Box, topology: Box) -> None:
  vrf_name = vlan.vrf
  if not vrf_name in topology.vrfs:
    common.error(
      f'VXLAN-enabled VLAN {vname} on node {node.name} that is part of VLAN bundle must belong to a global VRF',
      common.IncorrectValue,
      'evpn')
    return

  if not vname in topology.vlans:
    common.error(
      f'VLAN {vname} on node {node.name} that is part of VLAN bundle must be a global VLAN',
      common.IncorrectValue,
      'evpn')
    return

  if 'evpn' in node.vlans[vname]:                                   # VLAN that is part of a bundle cannot have EVI/RT/RD attributes
    common.error(
      f'VLAN {vname} on node {node.name} is part of a VLAN bundle {vrf_name} and cannot have EVPN-related attributes',
      common.IncorrectValue,
      'evpn')
    return

  if not topology.vrfs[vrf_name].evpn:
    topology.vrfs[vrf_name].evpn = {}                               # Make sure the global VRF EVPN attribute is a dictionary
  g_evpn = topology.vrfs[vrf_name].evpn
  if not 'evi' in g_evpn:                                           # If needed, set EVI attribute for the global VRF
    g_evpn.evi = topology.vlans[vname].id                           # ... to first VLAN ID encountered (lowest when auto-assigned)
  data.must_be_dict(node.vrfs[vrf_name],'evpn',f'nodes.{node.name}.vrfs.{vrf_name}',create_empty=True)
  evpn = node.vrfs[vrf_name].evpn                                   # Now set VRF EVPN parameters for node VRF
  evpn.evi = g_evpn.evi                                             # Copy EVI from global VRF
  set_transport(evpn,node)
  for k in ('vlans','vlan_ids'):
    if not k in evpn:                                               # Is this the first EVPN-enabled VLAN in this VRF?
      evpn[k] = []                                                  # ... create an empty list of VLANs
  evpn.vlans.append(vname)                                          # Finally, add VLAN name to the list of MAC VRF VLANs
  evpn.vlan_ids.append(topology.vlans[vname].id)                    # ... and a VLAN ID to list of EVPN-enabled VLAN tags

"""
Validate transit VNI values and register them with the VNI set
"""
def register_static_transit_vni(topology: Box) -> None:
  vni_set = _dataplane.get_id_set('vni')
  for vrf_name,vrf_data in topology.get('vrfs',{}).items():
    if vrf_data is None:
      continue
    data.must_be_dict(vrf_data,'evpn',f'vrfs.{vrf_name}',create_empty=False)

    transit_vni = data.get_from_box(vrf_data,'evpn.transit_vni')
    if data.is_true_int(transit_vni):
      vni_set.add(transit_vni)

  for n in topology.nodes.values():
    if not 'vrfs' in n:
      continue

    for vrf_name,vrf_data in n.vrfs.items():
      if data.get_from_box(vrf_data,'evpn.transit_vni'):
        common.error(
          f'evpn.transit_vni can be specified only on global VRFs (found in {vrf_name} on {n.name}',
          common.IncorrectValue,
          'evpn')

"""
Set transit VNI values for symmetrical IRB VRFs
"""
def get_next_vni(start_vni: int, used_vni_list: typing.List[int]) -> int:
  while True:
    start_vni = start_vni + 1
    if not start_vni in used_vni_list:
      return start_vni

def vrf_transit_vni(topology: Box) -> None:
  if not 'vrfs' in topology:
    return

  vni_list: typing.List[int] = []
  for vrf_name,vrf_data in topology.vrfs.items():               # First pass: build a list of statically configured VNIs
    if vrf_data is None:                                        # Skip empty VRF definitions
      continue
    vni = data.get_from_box(vrf_data,'evpn.transit_vni')
    if not data.is_true_int(vni):                               # Skip non-integer values, no need to check them at this time
      continue
    if vni in vni_list:
      common.error(
        f'VRF {vrf_name} is using the same EVPN transit VNI as another VRF',
        common.IncorrectValue,
        'evpn')
      continue
    elif _dataplane.is_id_used('vni',vni):
      common.error(
        f'VRF {vrf_name} is using an EVPN transit VNI that is also used as L2 VNI {vni}',
        common.IncorrectValue,
        'evpn')
      continue
    vni_list.append( vni )                                      # Insert it to detect duplicates elsewhere

  vni_start = topology.defaults.evpn.start_transit_vni
  for vrf_name,vrf_data in topology.vrfs.items():               # Second pass: set transit VNI values for VRFs with "transit_vni: True"
    if vrf_data is None:                                        # Skip empty VRF definitions
      continue
    if isinstance(data.get_from_box(vrf_data,'evpn.transit_vni'),str):
      continue                                                  # Skip transit_vni string values (will be checked in third pass)
    transit_vni = data.must_be_int(
                    vrf_data,
                    key='evpn.transit_vni',
                    path=f'vrfs.{vrf_name}',
                    module='evpn',
                    min_value=4096,                             # As recommended by Cisco, outside of VLAN range
                    max_value=16777215,
                    true_value=vni_start)                       # Make sure evpn.transit_vni is an integer
    if transit_vni == vni_start:                                # If we had to assign the default value, increment the default transit VNI
      vni_start = get_next_vni(vni_start,vni_list)

  for vrf_name,vrf_data in topology.vrfs.items():               # Third pass: set shared VNI values across VRFs
    if vrf_data is None:                                        # Skip empty VRF definitions
      continue
    transit_vni = data.get_from_box(vrf_data,'evpn.transit_vni')
    if not isinstance(transit_vni,str):                         # Skip if transit_vni is not a string
      continue
    if not transit_vni in topology.vrfs:                        # Does transit VNI refer to a valid VRF name?
      common.error(
        f'evpn.transit_vni "{transit_vni}" in VRF {vrf_name} does not refer to a valid VRF',
        common.IncorrectValue,
        'evpn')
      continue
    foreign_vni = data.get_from_box(topology.vrfs,f'{transit_vni}.evpn.transit_vni')
    if not data.is_true_int(foreign_vni):
      common.error(
        f'evpn.transit_vni "{transit_vni}" in VRF {vrf_name} refers to a VRF that does not have a valid evpn.transit_vni',
        common.IncorrectValue,
        'evpn')
      continue
    vrf_data.evpn.transit_vni = foreign_vni

def vrf_irb_setup(node: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)
  for vrf_name,vrf_data in node.get('vrfs',{}).items():
    if not 'af' in vrf_data or not 'evpn' in vrf_data:          # VRF without EVPN data or L3 information is definitely not doing IRB
      continue
    if not vrf_name in topology.get('vrfs',{}):                 # Makes no sense to configure IRB for local VRF
      continue

    g_vrf = topology.vrfs[vrf_name]                             # Pointer to global VRF data, will come useful in a second
    transit_vni = data.get_from_box(g_vrf,'evpn.transit_vni')
    evpn_mode = data.get_from_box(g_vrf,'evpn.mode') or 'symmetric_irb'
    if (transit_vni or evpn_mode=='symmetric_irb'):             # Transit VNI in global VRF => symmetrical IRB
      if not features.evpn.irb:                                 # ... does this device support IRB?
        common.error(
          f'VRF {vrf_name} on {node.name} uses symmetrical EVPN IRB which is not supported by {node.device} device',
          common.IncorrectValue,
          'evpn')
        continue
      if transit_vni:
        vrf_data.evpn.transit_vni = transit_vni                 # Make transit VNI is copied into the local VRF
      vrf_data.pop('ospf',None)                                 # ... and remove OSPF from EVPN IRB VRF
    else:
      if not features.evpn.asymmetrical_irb:                    # ... does this device asymmetrical IRB -- is it supported?
        common.error(
          f'VRF {vrf_name} on {node.name} uses asymmetrical EVPN IRB which is not supported by {node.device} device',
          common.IncorrectValue,
          'evpn')
        continue

class EVPN(_Module):

  def module_init(self, topology: Box) -> None:
    topology.defaults.vxlan.flooding = 'evpn'

  def module_pre_transform(self, topology: Box) -> None:
    register_static_transit_vni(topology)

  def module_post_node_transform(self, topology: Box) -> None:
    vrf_transit_vni(topology)

  def module_post_transform(self, topology: Box) -> None:
    for name,ndata in topology.nodes.items():
      if not 'evpn' in ndata.get('module',[]):        # Skip nodes without EVPN module
        continue
      if not 'vlans' in ndata:                        # Skip EVPN-enabled nodes without VLANs ( e.g. RR )
        if 'evpn' in ndata:                           # ... but make sure there's no evpn.vlans list left on them
          ndata.evpn.pop('vlans',None)
        continue
      node_vlan_check(ndata,topology)

  """
  Node post-transform: runs after VXLAN module

  Add 'evi' (EVPN Instance),'rd' and 'rt' attributes to VLANs that have a 'vni' attribute
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    enable_evpn_af(node,topology)

    vlan_list = data.get_from_box(node,'evpn.vlans') or data.get_from_box(node,'vxlan.vlans') # Get the list of VXLAN-enabled VLANs
    if not vlan_list:
      return                                                      # This could be a route reflector running EVPN

    _routing.router_id(node,'bgp',topology.pools)                 # Make sure we have a usable router ID

    for vname in vlan_list:
      vlan = node.vlans[vname]
      #
      # VLAN based service is used for VLANs that are not in a VRF or when the EVPN VLAN-Aware Bundle
      # Service is disabled (default)
      #
      if not 'vrf' in vlan or not data.get_from_box(node,'evpn.vlan_bundle_service'):
        vlan_based_service(vlan,vname,node,topology)
      else:
        vlan_aware_bundle_service(vlan,vname,node,topology)

    vrf_irb_setup(node,topology)
