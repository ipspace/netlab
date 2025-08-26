#
# VXLAN module
#
import typing

from box import Box

from ..augment import devices
from ..data.types import must_be_int, must_be_string
from ..utils import log
from ..utils import routing as _rp_utils
from . import _dataplane, _Module

"""
register_static_vni -- register all static VNIs
"""
def register_static_vni(topology: Box) -> None:
  _dataplane.create_id_set('vni')
  _dataplane.extend_id_set('vni',_dataplane.build_id_set(topology,'vlans','vni','topology'))
  _dataplane.set_id_counter('vni',topology.defaults.vxlan.start_vni,16777215)

  for n in topology.nodes.values():
    _dataplane.extend_id_set('vni',_dataplane.build_id_set(n,'vlans','vni',f'nodes.{n.name}'))


"""
validate_vxlan_list

* Create vxlan.vlans list with all known VLANs if the attribute is missing
* validate that the vxlan.vlans list is a list with valid local or global VLAN names

The heavy lifting is done in a shared _dataplane function
"""
def validate_vxlan_list(toponode: Box, obj_path: str, topology: Box) -> None:
  _dataplane.validate_object_reference_list(
    parent=toponode if not toponode is topology else None,
    parent_path=obj_path,
    topology=topology, 
    list_name='vxlan.vlans',
    reference_dictionary='vlans',
    reference_name='VLAN',
    module='vxlan')

"""
assign_vni -- Assign VNIs to VLANs listed in vxlan.vlans (or all VLANs if vxlan.vlans is missing)

Inputs:
* toponode: Topology or node
* obj_path: object path (topology or nodes.x)
* topology: pointer to topology so we can access global VLANs
"""
def assign_vni(toponode: Box, obj_path: str, topology: Box) -> None:
  vxlan_vlans = toponode.get('vxlan.vlans',None)
  if not vxlan_vlans:                                             # No VXLAN-enabled VLANs in the current data object ==> nothing to do
    return

  vni_ids = _dataplane.get_id_set('vni')
  for vname in vxlan_vlans:
    if not vname in toponode.get('vlans',{}):                     # Skip VXLAN-enabled VLANs that are not present on a node
      continue
    vlan_data = toponode.vlans[vname]
    vpath = f'{obj_path}.vlans.{vname}'
    if vname in topology.get('vlans',{}) and toponode != topology:
      if 'vni' in vlan_data and vlan_data.vni != topology.vlans[vname].get('vni',None):
        log.error(
          f'Cannot redefine VXLAN VNI for a global VLAN {vname} within node {toponode.name} VLAN data',
          log.IncorrectType,
          'vxlan')
      continue

    if 'vni' in vlan_data:
      if vlan_data.vni is False:                                  # Explicit request not to assign a VNI
        continue
      elif vlan_data.vni is True:                                 # Explicit request to assign VNI, pass through
        pass
      else:                                                       # Otherwise check that VNI is an int
        must_be_int(
          parent=vlan_data,
          key='vni',
          path=vpath,
          min_value=2,
          max_value=16777215,
          module='vxlan')
        continue

    vni_default = topology.defaults.vxlan.start_vni + vlan_data.id  # ... try to build VNI from VLAN ID
    if not vni_default in vni_ids:                                  # Is the VNI free?
      vlan_data.vni = vni_default                                   # ... great, take it
      vni_ids.add(vni_default)                                      # ... and add it to the list of used VNIs
    else:                                                           # Too bad, we had such a great idea but it failed
      vlan_data.vni = _dataplane.get_next_id('vni')                 # ... so take the next available VNI

#
# Set VTEP IPv4/IPv6 address
#
def node_set_vtep(node: Box, topology: Box) -> bool:
  # default vtep interface & interface name
  vtep_interface = node.loopback
  loopback_name = devices.get_loopback_name(node,topology)
  if not loopback_name:
    log.fatal("Can't find the loopback name of VXLAN-capable device {node.device}",module="vxlan",header=True)

  # Search for additional loopback interfaces with vxlan.vtep' flag, and use the first one
  for intf in node.interfaces:
    if intf.get('type', '') == 'loopback' and 'vxlan' in intf and intf.vxlan.get('vtep', False):
      vtep_interface = intf
      loopback_name = intf.ifname
      break

  if topology.defaults.vxlan.use_v6_vtep:
    vtep_af = 'ipv6'
    features = devices.get_device_features(node,topology.defaults)
    if not features.get('vxlan.vtep6'):
      log.error(
        f'Device {node.device} (node {node.name}) does not support VXLAN over IPv6',
        log.IncorrectValue,
        'vxlan')
      return False
  else:
    vtep_af = 'ipv4'

  if not vtep_af in vtep_interface:
    log.error(
      f'VXLAN module needs an {vtep_af.upper()} address on interface {loopback_name} of {node.name}',
      category=log.IncorrectValue,
      module='vxlan')
    return False

  # Save VTEP IP address (from the selected VTEP interface) and VTEP interface name
  #
  node.vxlan.vtep = _rp_utils.get_intf_address(vtep_interface[vtep_af])
  node.vxlan.vtep_interface = loopback_name
  return True

#
# Build VLAN-specific VTEP list
#
def build_vtep_list(vlan: Box, node: str, nodes: typing.List[str], topology: Box) -> list:
  vlan.vtep_list = []                                               # Start with an emtpy VTEP list
  local_vtep = topology.nodes[node].vxlan.vtep

  for n in nodes:
    if n == node:                                                   # Skip own node
      continue
    ndata = topology.nodes[n]
    if not 'vlans' in ndata:                                        # No VLANs on remote node, skip it
      continue
    remote_vtep = ndata.get('vxlan.vtep',None)                      # Get remote VTEP
    if remote_vtep is None:                                         # Remote node not using VXLAN?
      continue
    if remote_vtep == local_vtep:                                   # Skip anycast VTEP equal to local node
      continue
    if remote_vtep in vlan.vtep_list:                               # Remote anycast VTEP already in VTEP list?
      continue

    vni_match = filter(lambda x: x.get('vni',None) == vlan.vni,ndata.vlans.values())
    if list(vni_match):                                             # Is there a VLAN with matching VNI on remote node?
      vlan.vtep_list.append(remote_vtep)                            # ... if so, add remote VTEP to VLAN flood list

  return_value = vlan.vtep_list                                     # We'll return whatever we built
  if not vlan.vtep_list:                                            # ... but will remove empty VTEP list from VLAN data
    vlan.pop('vtep_list')

  return return_value

class VXLAN(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    register_static_vni(topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    flooding_values = ['static']
    for m in ['evpn']:
      if m in node.module:
        flooding_values.append(m)

    must_be_string(
      parent = node.vxlan,
      key = 'flooding',
      path = f'nodes.{node.name}.vxlan',
      valid_values = flooding_values)

  def module_post_node_transform(self, topology: Box) -> None:
    validate_vxlan_list(topology,'topology',topology)
    assign_vni(topology,'topology',topology)
    for n in topology.nodes.values():
      validate_vxlan_list(n,f'nodes.{n.name}',topology)
      assign_vni(n,f'nodes.{n.name}',topology)

  # We need multi-step post-transform node handling, so we have to do that in
  # module_post_transform
  #
  def module_post_transform(self, topology: Box) -> None:
    vxlan_domain_list: typing.Dict[str,list] = {}

    if not 'use_v6_vtep' in topology.vxlan:                         # Copy IPv6 VTEP setting into global parameter
      topology.vxlan.use_v6_vtep = topology.defaults.vxlan.use_v6_vtep

    for name,ndata in topology.nodes.items():
      if not 'vxlan' in ndata.get('module',[]):                     # Skip nodes without VXLAN module
        continue
      if not ndata.interfaces:
        log.error(
          f'VXLAN-enabled node {name} should be connected to at least one link',
          log.MissingValue,
          'vxlan')
        continue

      # Build the final per-node VXLAN list -- all VLANs with VNI attribute are VXLAN-enabled in one way or another
      #
      if 'vlans' in ndata:
        ndata.vxlan.vlans = [ vname for vname,vdata in ndata.vlans.items() if 'vni' in vdata and vdata.vni ]

      # Build the list of VRFs using VXLAN L3VNI
      #
      if 'vrfs' in ndata:
        l3vnis = [ vname for vname,vdata in ndata.vrfs.items() if vdata.get('evpn.transit_vni',False) ]
        if l3vnis:
          ndata.vxlan.l3vnis = l3vnis

      # Do we have a good reason to use VXLAN on this node?
      #
      if not ndata.vxlan.get('vlans',[]) and not ndata.vxlan.get('l3vnis',[]):
        ndata.module = [ m for m in ndata.module if m != 'vxlan' ]
        ndata.pop('vxlan',None)
        continue

      if not node_set_vtep(ndata,topology):                         # Set VTEP IP address
        continue

      vxlan_domain = ndata.vxlan.domain                             # Find VXLAN flooding domain name
      if not vxlan_domain in vxlan_domain_list:                     # Unknown VXLAN domain, prepare an empty list
        vxlan_domain_list[vxlan_domain] = []
      vxlan_domain_list[vxlan_domain].append(name)                  # Add current node to VXLAN domain list

    for domain,nodes in vxlan_domain_list.items():                  # Iterate over VXLAN flooding domains
      for node in nodes:                                            # ... and over all nodes in each domain
        ndata = topology.nodes[node]
        if ndata.vxlan.get('flooding') != 'static':                 # Skip nodes that are not using static replication lists
          continue

        vtep_set = set()
        for vlan in ndata.vlans.values():                           # Iterate over all VLANs defined in current node
          if 'vni' in vlan:                                         # Are we dealing with VXLAN-enabled VLAN?
            vtep_list = build_vtep_list(vlan,node,nodes,topology)   # Build VLAN-specific VTEP list
            vtep_set.update(vtep_list)                              # ... and add it to node-level VTEP set

        ndata.vxlan.vtep_list = sorted(list(vtep_set))              # Convert node-level VTEP set into a list
