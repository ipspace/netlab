#
# VRF module
#
import typing
from box import Box

from . import _Module,_routing
from .. import common
from .. import data
from .. import addressing
from ..data import get_from_box
from ..augment import devices
from ..augment import links

vlan_ids = Box({},default_box=True,box_dots=True)
vlan_next = Box({},default_box=True,box_dots=True)

#
# build_vrf_id_set: given an object (topology or node), create a set of RDs
# that appear in that object.
#
def build_vlan_id_set(obj: Box, attr: str) -> set:
  if 'vlans' in obj:
    return { v[attr] for v in obj.vlans.values() if isinstance(v,dict) and attr in v and v[attr] is not None }
  return set()

def populate_vlan_id_set(topology: Box) -> None:
  global vlan_ids, vlan_next

  if 'vlans' in topology:
    for k in ('id','vni'):
      vlan_ids[k] = build_vlan_id_set(topology,k)

  vlan_next['id'] = topology.defaults.vlan.start_vlan_id
  vlan_next['vni'] = topology.defaults.vlan.start_vni

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
# Validate VLAN attributes and set missing attributes:
#
# * VLAN and VNI
# * Subnet prefix
#
def validate_vlan_attributes(obj: Box, topology: Box) -> None:
  global vlan_ids

  if not 'vlans' in obj:
    return

  obj_name = 'global VLANs' if obj is topology else obj.name

  for vname in list(obj.vlans.keys()):
    if not obj.vlans[vname]:
      obj.vlans[vname] = Box({},default_box=True,box_dots=True)
    vdata = obj.vlans[vname]
    if not 'id' in vdata:                                           # When VLAN ID is not defined
      vdata.id = get_next_vlan_id('id')                             # ... take the next free VLAN ID from the list
    if not isinstance(vdata.id,int):                                # Now validate the heck out of VLAN ID
      common.error(f'VLAN ID for VLAN {vname} in {obj_name} must be an integer',common.IncorrectValue,'vlan')
      continue
    if vdata.id < 2 or vdata.id > 4094:
      common.error(f'VLAN ID for VLAN {vname} in {obj_name} must be between 2 and 4094',common.IncorrectValue,'vlan')
      continue

    if not 'vni' in vdata:                                          # When VNI is not defined
      vni_default = topology.defaults.vlan.start_vni + vdata.id     # ... try to build VNI from VLAN ID
      if not vni_default in vlan_ids.vni:                           # Is the VNI free?
        vdata.vni = vni_default                                     # ... great, take it
        vlan_ids.vni.add(vni_default)                               # ... and add it to the list of used VNIs
      else:                                                         # Too bad, we had such a great idea but it failed
        vdata.vni = get_next_vlan_id('vni')                         # ... so take the next available VNI
    if not isinstance(vdata.vni,int):                               # Not done yet, we still have to validate the VNI type and range
      common.error(f'VNI for VLAN {vname} in {obj_name} must be an integer',common.IncorrectValue,'vlan')
      continue
    if vdata.vni < 2 or vdata.vni > 16777215:
      common.error(f'VNI for VLAN {vname} in {obj_name} must be between 2 and 16777215',common.IncorrectValue,'vlan')
      continue

    vlan_pool = [ vdata.pool ] if 'pool' in vdata else []
    vlan_pool.extend(['vlan','lan'])
    pfx_list = links.augment_link_prefix(vdata,vlan_pool,topology.pools)
    vdata.prefix = addressing.rebuild_prefix(pfx_list)

"""
validate_link_vlan_attributes: limited implementation dealing with access VLANs

Make sure that:
* nobody is using 'trunk','native' or 'mode' attributes
* access VLAN is specified if the VLAN attribute is used
* access VLAN is not specified on a link and on an interface
"""
def validate_link_vlan_attributes(obj: Box,link: Box) -> bool:
  if not 'vlan' in obj:
    return True

  for attr in ('trunk','native','mode'):
    if attr in obj.vlan:
      common.error(
        f'VLAN link/interface attribute {attr} is not yet supported',
        common.IncorrectValue,
        'vlan')
      return False

  if not 'access' in obj.vlan:
    common.error(
      f"You must specify access VLAN when using 'vlan' link attribute\n... {link}",
      common.IncorrectValue,
      'vlan')
    return False
  else:
    if not obj is link and link.get('vlan',{}).get('access',None):
      common.error(
        f"You cannot specify access VLAN on a link and an attached node\n... {link}",
        common.IncorrectValue,
        'vlan')
      return False

  return True

"""
copy_vlan_attributes: copy prefix and link type from vlan to link
"""
def copy_vlan_attributes(vlan: Box, link: Box) -> None:
  if 'prefix' in vlan:
    link.prefix = vlan.prefix
  if not 'type' in link:
    link.type = vlan.get('type','lan')

"""
set_link_vlan_prefix: spaghetti mess trying to set a VLAN-derived prefix on a link

* Do we have link-level access VLAN? Fine, use prefix from global VLAN definition
* Do we have interface access VLAN on more than two interfaces? They must match, and
  we have to use prefix from global VLAN definition
* Otherwise we're dealing with a single access VLAN interface on a link. We're OK
  with using global or node VLAN definition
"""

def set_link_vlan_prefix(link: Box,topology: Box) -> None:
  if get_from_box(link,'vlan.access'):                    # Is access VLAN defined for the link?
    if not link.vlan.access in topology.get('vlans',{}):  # ... if so, it must be a global VLAN, or we wouldn't know 
      common.error(                                       # ... which definition to use
        f'Link-level access VLAN {link.vlan.access} should be defined as a global VLAN\n... {link}',
        common.IncorrectValue,
        'vlan')
      return
    copy_vlan_attributes(topology.vlans[link.vlan.access],link)
    return

  # No link-level access VLAN, build a list of interface access VLANs
  vlan_list = [ get_from_box(intf,'vlan.access') for intf in link.interfaces ]      # Collect all vlan.access settings
  vlan_list = [ vlan for vlan in vlan_list if vlan ]                                # ... and remove the empty ones

  if not vlan_list:                                   # No interface access VLAN? We're done, let's get out of here
    return

  if len(set(vlan_list)) > 1:                         # Oh my, more than one access VLAN. That can't be right
    common.error(
      f'Cannot use more than one access VLAN per link\n...{link}',
      common.IncorrectValue,
      'vlan')
    return

  link_vlan = vlan_list[0]                            # All interface access VLANs are the same, take the first one
  if link_vlan in topology.get('vlans',{}):           # Are we dealing with a global access VLAN?
    copy_vlan_attributes(topology.vlans[link_vlan],link)
  else:
    if len(vlan_list) > 1:                             # Access VLAN defined on more than one interface?
      common.error(
        f'An access VLAN used on more than one interface attached to a link must be a global VLAN\n... {link}',
        common.IncorrectValue,
        'vlan')
      return

    # Find the node using the access VLAN
    node = next(intf.node for intf in link.interfaces if get_from_box(intf,'access.vlan') == link_vlan)

    # Hope the VLAN is defined within the node, otherwise we're truly lost
    if link_vlan in topology.nodes[node].get('vlans',{}):
      copy_vlan_attributes(topology.nodes[node].vlans[link_vlan],link)
    else:
      common.error(
        f'Access VLAN used by node {node} should be defined globally or within the node\n... {link}',
        common.IncorrectValue,
        'vlan')

class VLAN(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    populate_vlan_id_set(topology)

    if not 'vlans' in topology:
      return

    populate_vlan_id_set(topology)
    validate_vlan_attributes(topology,topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if not 'vlans' in node:
      return

    for vname in node.vlans.keys():
      if 'vlans' in topology and vname in topology.vlans:
        for kw in ('prefix','id','vni'):
          if kw in node.vlans[vname]:
            common.error(
              f'Cannot set {kw} for VLAN {vname} on node {node.name} -- VLAN is defined globally',
              common.IncorrectValue,
              'vlan')
        node.vlans[vname] = topology.vlans[vname] + node.vlans[vname]

    validate_vlan_attributes(node,topology)

  def link_pre_transform(self, link: Box, topology: Box) -> None:
    if not validate_link_vlan_attributes(link,link):                    # Check link-level VLAN attributes
      return

    link_ok = True
    for intf in link.interfaces:
      link_ok = link_ok and validate_link_vlan_attributes(intf,link)    # Check interface VLAN attributes

    if not link_ok:
      return

    set_link_vlan_prefix(link,topology)

"""
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
"""
