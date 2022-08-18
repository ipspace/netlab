import typing

from . import _Module,_routing
from box import Box
from .. import common
from .. import data

def enable_evpn_af(node: Box, topology: Box) -> None:
  # evpn.use_ibgp was the old way of saying 'run EVPN over IBGP'
  #
  # This parameter has been replaced with evpn.session parameter and will eventually
  # disappear. In the meantime, 'evpn.use_ibgp' results in 'evpn.session' being
  # set to 'ibgp'
  if 'evpn' in node and 'use_ibgp' in node.evpn:
    data.must_be_bool(
      node,'evpn.use_ibgp',f'nodes.{node.name}.evpn.use_ibgp',
      module='evpn')
    node.evpn.session = ['ibgp'] if node.evpn.use_ibgp else ['ebgp']

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

class EVPN(_Module):

  def module_init(self, topology: Box) -> None:
    topology.defaults.vxlan.flooding = 'evpn'

  """
  Node pre-transform:
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    pass

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
      if not 'vrf' in vlan:                                               # VLAN-Based Service
        vlan_based_service(vlan,vname,node,topology)
      else:                                                               # VLAN-Aware Bundle Service or IRB
        vlan_aware_bundle_service(vlan,vname,node,topology)
