#
# VRF module
#
import typing
from box import Box

from . import _Module,_routing
from .. import common
from .. import data
from ..data import get_from_box
from ..augment import devices


vlan_ids: dict
vlan_next: dict

#
# build_vrf_id_set: given an object (topology or node), create a set of RDs
# that appear in that object.
#
def build_vlan_id_set(obj: Box, attr: str) -> set:
  if 'vlans' in obj:
    return { v[attr] for v in obj.vlans.values() if isinstance(v,dict) and attr in v and v[attr] is not None }
  return set()

def populate_vlan_id_set(topology: Box) -> None:
  global vlan_id_set, vlan_vni_set, vlan_next_id, vlan_next_vni

  if 'vlans' in topology:
    for k in ('id','vni'):
      vlan_ids[k] = build_vlan_id_set(topology,k)

  vlan_next['id'] = topology.defaults.vlan.start_vlan_id || 1000
  vlan_next['vni'] = topology.defaults.vlan.start_vni || 1000

  for n in topology.nodes.values():
    if 'vlans' in n:
      for k in ('id','vni'):
        vlan_ids[k] = vlan_ids[k].union(build_vlan_id_set(n,k))

def get_next_vlan_id(k : str) -> int:
  global vlan_ids,vlan_next

  if k not in vlan_ids or k not in vlan_next:   # pragma: no cover
    common.fatal(f'Invalid attribute {k} in get_next_vlan_id call')

  while vlan_next[k] in vlan_ids[k]:
    vlan_next[k] = vlan_next[k] + 1

  return vlan_next[k]

#
# Set RD values for all VRFs that have no RD attribute or RD value set to None (= auto-generate)
#
def set_vrf_ids(obj: Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return

  asn = None
  obj_name = 'global VRFs' if obj is topology else obj.name

  for vname,vdata in obj.vrfs.items():
    if vdata.get('rd',None) is None:
      asn = asn or get_rd_as_number(obj,topology)
      if not asn:
        common.error('Need a usable vrf.as or bgp.as to create auto-generated VRF RD for {vname} in {obj_name}',
          common.MissingValue,
          'vrf')
        return
      vdata.rd = get_next_vrf_id(asn)

class VLAN(_Module):

  def module_pre_default(self, topology: Box) -> None:
    for attr_set in ['global','node']:
      if not 'vlans' in topology.defaults.attributes[attr_set]:
        topology.defaults.attributes[attr_set].append('vlans')

  def module_pre_transform(self, topology: Box) -> None:
    populate_vlan_id_set(topology)

    if not 'vlans' in topology:
      return

    normalize_vrf_ids(topology)
    populate_vrf_id_set(topology)
    set_vrf_ids(topology,topology)
    set_import_export_rt(topology,topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if not 'vlans' in node:
      return

    for vname in node.vrfs.keys():
      if 'vrfs' in topology and vname in topology.vrfs:
        node.vrfs[vname] = topology.vrfs[vname] + node.vrfs[vname]

    set_vrf_ids(node,topology)
    set_import_export_rt(node,topology)

  def link_pre_transform(self, link: Box, topology: Box) -> None:
    pass

  def node_post_transform(self, node: Box, topology: Box) -> None:
    vrf_count = 0
    for ifdata in node.interfaces:
      if 'vrf' in ifdata:
        vrf_count = vrf_count + 1
        if 'vrfs' in topology and ifdata.vrf in topology.vrfs:
          node.vrfs[ifdata.vrf] = topology.vrfs[ifdata.vrf] + node.vrfs[ifdata.vrf]

        if not node.vrfs[ifdata.vrf]:
          common.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} is not defined in the node or globally',
            common.MissingValue,
            'vrf')
          continue
        if not node.vrfs[ifdata.vrf].rd:
          common.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} does not have a usable RD',
            common.MissingValue,
            'vrf')
          continue

        for af in ['v4','v6']:
          if f'ip{af}' in ifdata:
            node.af[f'vpn{af}'] = True
            node.vrfs[ifdata.vrf].af[f'ip{af}'] = True

    if not vrf_count:                # Remove VRF module from the node if the node has no VRFs
      node.module = [ m for m in node.module if m != 'vrf' ]
    else:
      node.vrfs = node.vrfs or {}     # ... otherwise make sure the 'vrfs' dictionary is not empty
      vrfidx = 100
      for v in node.vrfs.values():    # We need unique VRF index to create OSPF processes
        v.vrfidx = vrfidx
        vrfidx = vrfidx + 1

      validate_vrf_route_leaking(node)

    # Finally, set BGP router ID if we set BGP AS number
    #
    if get_from_box(node,'bgp.as') and not get_from_box(node,'bgp.router_id'):
      _routing.router_id(node,'bgp',topology.pools)
