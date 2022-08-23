import typing

from . import _Module,_routing
from box import Box
from .. import common
from .. import data
from ..augment import devices

def enable_evpn_af(node: Box, topology: Box) -> None:
  bgp_session = data.get_from_box(node,'evpn.session') or []

  # Enable EVPN AF on all BGP neighbors with the correct session type
  # that also use EVPN module
  #
  for bn in node.bgp.get('neighbors',[]):
    if bn.type in bgp_session and 'evpn' in topology.nodes[bn.name].get('module'):
      bn.evpn = True

def vlan_based_service(vlan: Box, vname: str, node: Box, topology: Box) -> None:
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

  g_evpn = topology.vrfs[vrf_name].evpn
  if not 'evi' in g_evpn:                                           # If needed, set EVI attribute for the global VRF
    g_evpn.evi = topology.vlans[vname].id                           # ... to VLAN ID

  evpn = node.vrfs[vrf_name].evpn                                   # Now set VRF EVPN parameters for node VRF
  evpn.evi = g_evpn.evi                                             # Copy EVI from global VRF
  for k in ('vlans','vlan_ids'):
    if not k in evpn:                                               # Is this the first EVPN-enabled VLAN in this VRF?
      evpn[k] = []                                                  # ... create an empty list of VLANs
  evpn.vlans.append(vname)                                          # Finally, add VLAN name to the list of MAC VRF VLANs
  evpn.vlan_ids.append(topology.vlans[vname].id)                    # ... and a VLAN ID to list of EVPN-enabled VLAN tags

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
    if not isinstance(vni,int):
      continue
    if vni in vni_list:
      common.error(
        f'VRF {vrf_name} is using the same EVPN transit VNI as another VRF',
        common.IncorrectValue,
        'evpn')
      continue

  vni_start = topology.defaults.evpn.start_transit_vni
  for vrf_name,vrf_data in topology.vrfs.items():               # Second pass: set transit VNI values for VRFs with "transit_vni: True"
    if vrf_data is None:                                        # Skip empty VRF definitions
      continue
    transit_vni = data.must_be_int(
                    vrf_data,
                    key='evpn.transit_vni',
                    path=f'vrfs.{vrf_name}',
                    module='evpn',
                    true_value=vni_start)                       # Make sure evpn.transit_vni is an integer
    if transit_vni == vni_start:                                # If we had to assign the default value, increment the default transit VNI
      vni_start = get_next_vni(vni_start,vni_list)

def vrf_irb_setup(node: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)
  for vrf_name,vrf_data in node.get('vrfs',{}).items():
    if not 'af' in vrf_data or not 'evpn' in vrf_data:          # VRF without EVPN data or L3 information is definitely not doing IRB
      continue
    if not vrf_name in topology.get('vrfs',{}):                 # Makes no sense to configure IRB for local VRF
      continue

    g_vrf = topology.vrfs[vrf_name]                             # Pointer to global VRF data, will come useful in a second
    if 'transit_vni' in g_vrf.get('evpn',{}):                   # Transit VNI in global VRF => symmetrical IRB
      if not features.evpn.irb:                                 # ... does this device support IRB?
        common.error(
          f'VRF {vrf_name} on {node.name} uses symmetrical EVPN IRB which is not supported by {node.device} device',
          common.IncorrectValue,
          'evpn')
        continue
      vrf_data.evpn.transit_vni = g_vrf.evpn.transit_vni        # Make transit VNI is copied into the local VRF
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
    vrf_transit_vni(topology)

  """
  Node post-transform: runs after VXLAN module

  Add 'evi' (EVPN Instance),'rd' and 'rt' attributes to VLANs that have a 'vni' attribute
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    enable_evpn_af(node,topology)

    vlan_list = data.get_from_box(node,'vxlan.vlans') or []       # Get the list of VXLAN-enabled VLANs
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
