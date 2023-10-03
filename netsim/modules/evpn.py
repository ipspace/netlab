import typing

from . import _Module,_routing,_dataplane
from box import Box
from ..utils import log
from .. import data
from ..data.validate import must_be_int,must_be_dict,must_be_string
from ..augment import devices

"""
validate_evpn_list

* If missing, create evpn.vlans list with all VLANs with 'vni' attribute
* Validate that the evpn.vlans list is a list with valid local or global VLAN names
* If missing, create evpn.vrfs list with all VRFs with 'evpn.transit_vni' attribute
* Validate that the evpn.vrfs list is a list with valid local or global VRF names

The heavy lifting is done in a shared _dataplane function
"""
def validate_evpn_lists(toponode: Box, obj_path: str, topology: Box, create: bool = False) -> None:
  _dataplane.validate_object_reference_list(
    parent=toponode if not toponode is topology else None,
    parent_path=obj_path,
    topology=topology, 
    list_name='evpn.vlans',
    reference_dictionary='vlans',
    reference_name='VLAN',
    create_default=create,
    merge_topology=False,
    default_filter=lambda v: 'vni' in v and v.vni,
    module='evpn')

  _dataplane.validate_object_reference_list(
    parent=toponode if not toponode is topology else None,
    parent_path=obj_path,
    topology=topology, 
    list_name='evpn.vrfs',
    reference_dictionary='vrfs',
    reference_name='VLAN',
    create_default=create,
    merge_topology=False,
    default_filter=lambda v: False if not isinstance(v,Box) else v.get('evpn.transit_vni',False),
    module='evpn')

def enable_evpn_af(node: Box, topology: Box) -> None:
  bgp_session = node.get('evpn.session',[])

  # Enable EVPN AF on all BGP neighbors with the correct session type
  # that also use EVPN module
  #
  for bn in node.bgp.get('neighbors',[]):
    if bn.type in bgp_session and 'evpn' in topology.nodes[bn.name].get('module'):
      bn.evpn = True

def get_usable_evpn_asn(topology: Box) -> int:
  asn = ( topology.get('evpn.as',None) or
          topology.get('vrf.as',None) or
          topology.get('bgp.as',None) )

  if asn and data.is_true_int(asn):
    return asn

  log.error(
    f'Cannot get a usable global AS number to use in EVPN route targets',
    log.IncorrectValue,
    'evpn',hint='asn')
  return 0

def vlan_based_service(vlan: Box, vname: str, topology: Box) -> None:
  evpn  = vlan.evpn
  epath = f'vlans.{vname}.evpn'
  evpn.evi = evpn.evi or vlan.id                                    # Default EVI value: VLAN ID
  asn = get_usable_evpn_asn(topology)
  must_be_int(
    evpn,'evi',epath,
    module='evpn',
    min_value=1,max_value=65535)                                    # Check EVI data type in range
  for rt in ('import','export'):                                    # Default RT value
    if not rt in evpn:                                              # ... BGP ASN:vlan ID
      evpn[rt] = [ f"{asn}:{evpn.evi}" ]

def vlan_aware_bundle_service(vlan: Box, vname: str, topology: Box) -> None:
  vrf_name = vlan.vrf
  if not vrf_name in topology.vrfs:
    log.error(
      f'VXLAN-enabled VLAN {vname} that is part of VLAN bundle must belong to a global VRF',
      log.IncorrectValue,
      'evpn')
    return

  if 'evpn' in vlan:                                                # VLAN that is part of a bundle cannot have EVI/RT/RD attributes
    log.error(
      f'VLAN {vname} is part of a VLAN bundle {vrf_name} and cannot have EVPN-related attributes',
      log.IncorrectValue,
      'evpn')
    return

  vrf = topology.vrfs[vrf_name]
  must_be_dict(
    parent=vrf,
    key='evpn',
    path=f'vrfs.{vrf_name}',
    create_empty=True)
 
  evpn = vrf.evpn
  vlan.evpn.bundle = evpn.bundle                                    # Copy the bundle type into VLAN
  if not 'evi' in evpn:                                             # If needed, set EVI attribute for the global VRF
    evpn.evi = vrf.id                                               # ... to the VRF ID

  vlan.evpn.evi = evpn.evi
  for k in ('vlans','vlan_ids'):
    if not k in evpn:                                               # Is this the first EVPN-enabled VLAN in this VRF?
      evpn[k] = []                                                  # ... create an empty list of VLANs
  evpn.vlans.append(vname)                                          # Finally, add VLAN name to the list of MAC VRF VLANs
  evpn.vlan_ids.append(topology.vlans[vname].id)                    # ... and a VLAN ID to list of EVPN-enabled VLAN tags


"""
Figure out whether we have to treat a VLAN as part of a VLAN bundle or an independent VLAN service
"""

def get_vlan_bundle_flag(vlan: Box, vname: str, topology: Box) -> bool:
  if not 'vrf' in vlan:                                             # VLAN not part of a VRF ==> VLAN service
    return False

  vrf = topology.vrfs[vlan.vrf]
  if not vrf.get('evpn.bundle',None):                               # VRF does not have evpn.bundle attribute ==> VLAN service
    return False

  must_be_string(
    parent=vrf,
    key='evpn.bundle',
    path=f'vrfs.{vlan.vrf}',
    module='evpn',
    valid_values=topology.defaults.evpn.attributes.bundle)          # Validate evpn.bundle value

  return True

"""
Create VLAN services -- either as independent VLANs or as a VRF-based bundle
"""

def create_vlan_service(vname: str, topology: Box) -> None:
  vlan = topology.vlans[vname]
  if not get_vlan_bundle_flag(vlan,vname,topology):
    vlan_based_service(vlan,vname,topology)
  else:
    vlan_aware_bundle_service(vlan,vname,topology)

"""
Validate that there's no evpn.bundle setting on node VRFs
"""

def validate_no_node_vrf_bundle(node: Box, topology: Box) -> None:
  if not 'vrfs' in node:                                            # No VRFs defined in the node, move on
    return
  for vname,vdata in node.vrfs.items():
    if not vdata.get('evpn.bundle',None):                           # EVPN bundle not set in VRF, move on
      continue
    log.error(
      f'VRF {vname} in node {node.name} cannot have evpn.bundle attribute',
      log.IncorrectValue,
      'evpn',
      hint='node_bundle')

"""
Validate transit VNI values and register them with the VNI set
"""
def register_static_transit_vni(topology: Box) -> None:
  vni_set = _dataplane.get_id_set('vni')
  for vrf_name,vrf_data in topology.get('vrfs',{}).items():
    must_be_dict(vrf_data,'evpn',f'vrfs.{vrf_name}',create_empty=False)

    transit_vni = vrf_data.get('evpn.transit_vni',None)
    if data.is_true_int(transit_vni):
      if transit_vni in vni_set:
        log.error(
          f'transit VNI {transit_vni} for VRF {vrf_name} is already used elsewhere',
          log.IncorrectValue,
          'evpn')
        continue
      vni_set.add(transit_vni)

  for n in topology.nodes.values():
    if not 'vrfs' in n:
      continue

    for vrf_name,vrf_data in n.vrfs.items():
      if vrf_data.get('evpn.transit_vni',None):
        log.error(
          f'evpn.transit_vni can be specified only on global VRFs (found in {vrf_name} on {n.name}',
          log.IncorrectValue,
          'evpn')

"""
Set transit VNI values for symmetrical IRB VRFs (REFACTOR to use _dataplane)
"""
def get_next_vni(start_vni: int, used_vni_list: typing.List[int]) -> int:
  while True:
    start_vni = start_vni + 1
    if not start_vni in used_vni_list:
      return start_vni

def vrf_transit_vni(topology: Box) -> None:
  if not 'vrfs' in topology:
    return

  vni_list: typing.List[int] = []                               # List of static transit VNIs
  vni_error = False                                             # "A horrible error" flag that causes abort after the first loop
  vni_count = 0                                                 # Number of VRFs with evpn.transit_vni
  evpn_transport = topology.get('evpn.transport','vxlan')       # Default to VXLAN transport

  for vrf_name,vrf_data in topology.vrfs.items():               # First pass: build a list of statically configured VNIs
    vni = vrf_data.get('evpn.transit_vni',None)                 # transit_vni makes no sense with MPLS transport
    if vni and evpn_transport != 'vxlan':
      log.error(
        f'evpn.transit_vni in VRF {vrf_name} is not allowed with mpls evpn.transport',
        log.IncorrectValue,
        'evpn')
      vni_error = True
      continue

    if not vni is None:
      vni_count = vni_count + 1                                 # Count number of VRFs with evpn.transit_vni attribute
    if not data.is_true_int(vni):                               # Skip non-integer values, no need to check them at this time
      continue
    if vni in vni_list:
      log.error(
        f'VRF {vrf_name} is using the same EVPN transit VNI as another VRF',
        log.IncorrectValue,
        'evpn')
      continue  
    vni_list.append( vni )                                      # Insert it to detect duplicates elsewhere

  if vni_error:                                                 # Found serious errors, makes no sense to continue
    return
  if not vni_count:                                             # No VRF found with evpn.transit_vni, no need to waste further CPU cycles
    return

  vni_start = topology.defaults.evpn.start_transit_vni
  for vrf_name,vrf_data in topology.vrfs.items():               # Second pass: set transit VNI values for VRFs with "transit_vni: True"
    if isinstance(vrf_data.get('evpn.transit_vni',None),str):
      continue                                                  # Skip transit_vni string values (will be checked in third pass)
    transit_vni = must_be_int(
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
    transit_vni = vrf_data.get('evpn.transit_vni',None)
    if not isinstance(transit_vni,str):                         # Skip if transit_vni is not a string
      continue
    if not transit_vni in topology.vrfs:                        # Does transit VNI refer to a valid VRF name?
      log.error(
        f'evpn.transit_vni "{transit_vni}" in VRF {vrf_name} does not refer to a valid VRF',
        log.IncorrectValue,
        'evpn')
      continue
    foreign_vni = topology.vrfs.get(f'{transit_vni}.evpn.transit_vni',None)
    if not data.is_true_int(foreign_vni):
      log.error(
        f'evpn.transit_vni "{transit_vni}" in VRF {vrf_name} refers to a VRF that does not have a valid evpn.transit_vni',
        log.IncorrectValue,
        'evpn')
      continue
    vrf_data.evpn.transit_vni = foreign_vni

def vrf_irb_setup(topology: Box) -> None:
  for vrf_name,vrf_data in topology.get('vrfs',{}).items():
    if not 'evpn' in vrf_data:                                  # VRF without EVPN data is definitely not doing IRB
      continue
    
    if not 'evi' in vrf_data.evpn:
      vrf_data.evpn.evi = vrf_data.id

"""
Copy global evpn.vlans, evpn.vrfs, and evpn.transport into node evpn data structures.
"""
def copy_global_evpn_lists(node: Box, topology: Box) -> None:
  g_evpn = topology.get('evpn',{})
  for k in ('vlans','vrfs','transport'):
    if k in g_evpn and not k in node.evpn:
      node.evpn[k] = g_evpn[k]

"""
Trim node evpn.vlans and evpn.vrfs lists to refer only to on-node VLANs and VRFs
"""
def trim_node_evpn_lists(node: Box) -> None:
  if not 'evpn' in node:                                        # No on-node EVPN structures, get out of here
    return

  for ref_list in ('vlans','vrfs'):
    if ref_list in node.evpn:                                   # Filter EVPN list to refer only to on-node objects
      node.evpn[ref_list] = [ obj_name for obj_name in node.get(ref_list,{}).keys() if obj_name in node.evpn[ref_list] ]

"""
Set local evpn.rd for evpn-enabled VLANs and VRFs
"""
def set_local_evpn_rd(node: Box) -> None:
  for obj in ('vlans','vrfs'):
    if not obj in node:
      continue

    for o_name,o_data in node[obj].items():                     # Iterate over VLANs/VRFs
      if not 'evpn' in o_data:
        continue                                                # Skip non-EVPN objects
      if not 'evi' in o_data.evpn:
        log.error(
          f'{obj}.{o_name} on node {node.name} has EVPN attributes but no evpn.evi ({o_data.evpn})',
          log.IncorrectValue,
          'evpn')
        continue
      #
      # Set local RD unless a static RD was set
      if not 'rd' in o_data.evpn:
        o_data.evpn.rd = f'{node.bgp.router_id}:{o_data.evpn.evi}'

"""
Check whether all VLANs needed for an asymmetric IRB VRF are present on a node
"""

def check_asym_vlan(vrf_name: str, node: Box, topology: Box) -> None:
  if not 'vlans' in topology:                                   # No global VLANs, nothing to check
    return

  for vl_name,vl_data in topology.vlans.items():                # Iterate over global VLANs
    if not vrf_name in vl_data.get('vrf',''):                   # The VLAN is not in current VRF, skip it
      continue

    if not 'evpn' in vl_data:                                   # VLAN is not EVPN-enabled, so it doesn't have to be present everywhere
      continue

    if vl_name in node.get('vlans',{}):                         # Is the VLAN present on the node?
      continue                                                  # Yeah, everything OK

    log.error(
      f'VLAN {vl_name} -- part of VRF {vrf_name} that uses asymmetric IRB -- is not present on node {node.name}',
      log.IncorrectValue,
      module='evpn',
      hint='irb_group')

"""
Check whether VXLAN IRB mode is supported by the device
"""
def check_node_vrf_irb(node: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)
  evpn_transport = node.get('evpn.transport','vxlan')

  for vrf_name,vrf_data in node.get('vrfs',{}).items():
    if not vrf_data.get('af',None):                             # Cannot do IRB without L3 addresses ;)
      continue

    symmetric_irb = vrf_data.get('evpn.transit_vni',False) or evpn_transport == 'mpls'
    if symmetric_irb:
      if not features.evpn.irb and evpn_transport == 'vxlan':   # ... does this device support IRB?
        log.error(
          f'VRF {vrf_name} on {node.name} uses symmetrical EVPN IRB which is not supported by {node.device} device',
          log.IncorrectValue,
          'evpn')
        continue

      vrf_data.pop('ospf',None)                                 # Remove OSPF from EVPN IRB VRF
    else:
      if not features.evpn.asymmetrical_irb:                    # ... does this device asymmetrical IRB -- is it supported?
        log.error(
          f'VRF {vrf_name} on {node.name} uses asymmetrical EVPN IRB which is not supported by {node.device} device',
          log.IncorrectValue,
          'evpn')
        continue

      check_asym_vlan(vrf_name,node,topology)

"""
Check whether the node supports the requested EVPN bundle type
"""

def check_node_vrf_bundle(node: Box, topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)      # Get device features
  for vrf_name,vrf_data in node.get('vrfs',{}).items():               # Iterate over all VRFs defined on the device
    b_type = vrf_data.get('evpn.bundle',None)                         # Get evpn.bundle value, skip if not defined
    if not b_type:
      continue
    if not b_type in features.evpn.bundle:                            # EVPN bundle type not supported by the device
      log.error(
        f"'{b_type}'' EVPN bundle service used in VRF {vrf_name} is not supported by device {node.device} (node: {node.name})",
        log.IncorrectValue,
        'evpn')

class EVPN(_Module):

  def module_init(self, topology: Box) -> None:
    topology.defaults.vxlan.flooding = 'evpn'

  def module_pre_transform(self, topology: Box) -> None:
    register_static_transit_vni(topology)
    must_be_string(
      parent=topology,
      key='evpn.transport',
      path='topology',
      valid_values=['vxlan','mpls'],
      module='evpn')

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    validate_no_node_vrf_bundle(node,topology)

  def module_post_node_transform(self, topology: Box) -> None:
    validate_evpn_lists(topology,'topology',topology,create=True)
    for n in topology.nodes.values():
      validate_evpn_lists(n,f'nodes.{n.name}',topology,create=False)

    vrf_transit_vni(topology)
    for vname in topology.get('evpn.vlans',[]):
      create_vlan_service(vname,topology)

    vrf_irb_setup(topology)

  """
  Node post-transform: runs after VXLAN module

  * Enable EVPN address family
  * Build node-specific evpn.vlans and epvn.vrfs lists
  * Calculate final RD values

  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    enable_evpn_af(node,topology)
    _routing.router_id(node,'bgp',topology.pools)                 # Make sure we have a usable router ID
    copy_global_evpn_lists(node,topology)
    check_node_vrf_irb(node,topology)
    check_node_vrf_bundle(node,topology)
    trim_node_evpn_lists(node)
    set_local_evpn_rd(node)
