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
vlan_mode_kwd = [ 'bridge', 'irb', 'route' ]

#
# build_vrf_id_set: given an object (topology or node), create a set of RDs
# that appear in that object.
#
def build_vlan_id_set(obj: Box, attr: str, objname: str) -> set:
  if 'vlans' in obj:
    if not isinstance(obj.vlans,dict):    # pragma: no cover
      common.fatal(f'Found a "vlans" setting that is not a dictionary in {objname}','vlan')
      return set()

    return { v[attr] for v in obj.vlans.values() if isinstance(v,dict) and attr in v and v[attr] is not None }
  return set()

def populate_vlan_id_set(topology: Box) -> None:
  global vlan_ids, vlan_next

  for k in ('id','vni'):
    vlan_ids[k] = build_vlan_id_set(topology,k,'topology')

  vlan_next['id'] = topology.defaults.vlan.start_vlan_id
  vlan_next['vni'] = topology.defaults.vlan.start_vni

  for n in topology.nodes.values():
    if 'vlans' in n:
      for k in ('id','vni'):
        vlan_ids[k] = vlan_ids[k].union(build_vlan_id_set(n,k,n.name))

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

  obj_name = 'global VLANs' if obj is topology else obj.name
  default_fwd_mode = get_from_box(obj,'vlan.mode')                # Get node-wide VLAN forwarding mode
  if default_fwd_mode:                                            # ... is it set?
    default_fwd_mode = str(default_fwd_mode)                      # Convert it to string so we don't have to deal with weird types
    if not default_fwd_mode in vlan_mode_kwd:                     # ... and check keyword validity
      common.error(
        f'Invalid vlan.mode setting {default_fwd_mode} in {obj_name}',
        common.IncorrectValue,
        'vlan')

  if not 'vlans' in obj:
    return

  for vname in list(obj.vlans.keys()):
    if not obj.vlans[vname]:
      obj.vlans[vname] = Box({},default_box=True,box_dots=True)

    vdata = obj.vlans[vname]

    if 'mode' in vdata:                                             # Do we have 'mode' set in the VLAN definition?
      if not vdata.mode in vlan_mode_kwd:                           # ... check the keyword value 
        common.error(
          f'Invalid VLAN mode setting {vdata.mode} in VLAN {vname} in {obj_name}',
          common.IncorrectValue,
          'vlan')
    else:
      if default_fwd_mode:                                          # Propagate default VLAN forwarding mode if needed
        vdata.mode = default_fwd_mode

    if 'mode' in vdata and vdata.mode == 'route':                   # Throw out attempts to have routed interfaces
      common.error(f'VLAN routed interfaces not yet supported: VLAN {vname} in {obj_name}',common.IncorrectValue,'vlan')
    if not 'id' in vdata:                                           # When VLAN ID is not defined
      vdata.id = get_next_vlan_id('id')                             # ... take the next free VLAN ID from the list
    if not isinstance(vdata.id,int):                                # Now validate the heck out of VLAN ID
      common.error(f'VLAN ID {vdata.id} for VLAN {vname} in {obj_name} must be an integer',common.IncorrectValue,'vlan')
      continue
    if vdata.id < 2 or vdata.id > 4094:
      common.error(f'VLAN ID {vdata.id} for VLAN {vname} in {obj_name} must be between 2 and 4094',common.IncorrectValue,'vlan')
      continue

    if not 'vni' in vdata:                                          # When VNI is not defined
      vni_default = topology.defaults.vlan.start_vni + vdata.id     # ... try to build VNI from VLAN ID
      if not vni_default in vlan_ids.vni:                           # Is the VNI free?
        vdata.vni = vni_default                                     # ... great, take it
        vlan_ids.vni.add(vni_default)                               # ... and add it to the list of used VNIs
      else:                                                         # Too bad, we had such a great idea but it failed
        vdata.vni = get_next_vlan_id('vni')                         # ... so take the next available VNI
    if not isinstance(vdata.vni,int):                               # Not done yet, we still have to validate the VNI type and range
      common.error(f'VNI {vdata.vni} for VLAN {vname} in {obj_name} must be an integer',common.IncorrectValue,'vlan')
      continue
    if vdata.vni < 2 or vdata.vni > 16777215:
      common.error(f'VNI {vdata.vni} for VLAN {vname} in {obj_name} must be between 2 and 16777215',common.IncorrectValue,'vlan')
      continue

    vlan_pool = [ vdata.pool ] if 'pool' in vdata else []
    vlan_pool.extend(['vlan','lan'])
    pfx_list = links.augment_link_prefix(vdata,vlan_pool,topology.pools)
    vdata.prefix = addressing.rebuild_prefix(pfx_list)

"""
check_link_vlan_attributes: check correctness of VLAN link attributes

* known attributes only
* attribute types must be correct
* VLANs used in attribute types must be defined
"""

vlan_link_attr: dict = {
  'access': { 'type' : str, 'vlan': True, 'single': True },
  'native': { 'type' : str, 'vlan': True, 'single': True },
  'mode':   { 'type' : str },
  'trunk' : { 'type' : dict,'vlan': True }
}

def check_link_vlan_attributes(obj: Box, link: Box, v_attr: Box, topology: Box) -> bool:
  global vlan_link_attr
  if not 'vlan' in obj:
    return True

  if not isinstance(obj.vlan,dict):                               # Basic sanity check: VLAN attribute must be a dictionary
    common.error(
      f'vlan link attribute must be a dictionary\n... {link}',
      common.IncorrectValue,
      'vlan')
    return False

  node_error = f' in node {obj.node}' if not obj is link else ''  # Prepare for error checking
  link_ok = True

  for attr in obj.vlan.keys():                                    # Check for unexpected attributes
    if not attr in vlan_link_attr:
      common.error(
        f'Unknown VLAN attribute {attr}{node_error}\n... {link}',
        common.IncorrectValue,
        'vlan')
      link_ok = False

  for attr in vlan_link_attr.keys():                              # Loop over VLAN attributes
    if not attr in obj.vlan:                                      # ... not present, skip
      continue

    a_type = vlan_link_attr[attr]['type']
    if not isinstance(obj.vlan[attr],a_type):                     # Is the attribute type correct?
      if a_type is dict and isinstance(obj.vlan[attr],list):      # ... only exception: convert list to dict
        obj.vlan[attr] = { vname: {} for vname in obj.vlan[attr] }
      else:
        common.error(
          f'VLAN attribute {attr}{node_error} must be a {a_type.__name__}\n... {link}',
          common.IncorrectValue,
          'vlan')  
        link_ok = False
        continue

    if not 'vlan' in vlan_link_attr[attr]:                        # If this attribute does not contain VLAN names, skip the rest
      continue
                                                                  # Build a list of VLANs out of a string or a dict
    vlan_list = [ obj.vlan[attr] ] if isinstance(obj.vlan[attr],str) else obj.vlan[attr].keys()
    if not attr in v_attr:                                        # Prepare attribute collection dictionary if needed
      v_attr[attr].list = []
      v_attr[attr].set = set()
      v_attr[attr].node_set = set()
      v_attr[attr].use_count = 0

    v_attr[attr].list.extend(vlan_list)                           # ... and add collected VLANs to attribute dictionary
    v_attr[attr].set.update(vlan_list)
    v_attr[attr].use_count = v_attr[attr].use_count + 1

    for vname in vlan_list:                                       # Check that VLANs exist
      if vname in topology.get('vlans',{}):
        continue
      if not obj is link and vname in topology.nodes[obj.node].get('vlans',{}):
        v_attr[attr].node_set.add(obj.node)
        continue
      common.error(
        f'VLAN {vname} used in vlan.{attr}{node_error} is not defined\n... {link}',
        common.IncorrectValue,
        'vlan')
      link_ok = False

  return link_ok

"""
validate_link_vlan_attributes: check semantical correctness of VLAN attributes

* 'trunk' and 'access' cannot be mixed
* 'native' is valid only with 'trunk'
* 'access' and 'native' should have a single value
"""
def validate_link_vlan_attributes(link: Box,v_attr: Box,topology: Box) -> bool:
  global vlan_link_attr

  if 'trunk' in v_attr and 'access' in v_attr:
    common.error(
      f"Cannot mix trunk and access VLANs on the same link\n... {link}",
      common.IncorrectValue,
      'vlan')
    return False

  if 'native' in v_attr and not 'trunk' in v_attr:
    common.error(
      f"Native VLAN is valid only on VLAN trunks\n... {link}",
      common.IncorrectValue,
      'vlan')
    return False

  link_ok = True

  for attr in vlan_link_attr.keys():                              # Loop over VLAN attributes
    if not attr in v_attr:                                        # ... not present, skip
      continue

    if not 'vlan' in v_attr:                                      # Not a list of VLANs, no further checks necessary
      continue

    if v_attr[attr].use_count > 1:                                # Is this attribute used in more than one place on the link?
      for vname in v_attr[attr].set:                              # Iterate over the VLAN set
        if not vname in topology.get('vlans',{}):                 # ... and check that all VLANs used this way are globally defined
          common.error(
            f"VLAN {vname} used in more than one place on the same link must be a global VLAN\n... {link}",
            common.IncorrectValue,
            'vlan')
          link_ok = False

    if not 'single' in v_attr:                                    # Does the attribute require a consistent VLAN across the link?
      continue

    if len(v_attr[attr].set) > 1:                                 # ... if so, check the length of the VLAN set
      common.error(
        f"Cannot use more than one {attr} VLAN on the same link\n... {link}",
        common.IncorrectValue,
        'vlan')
      return False

  return link_ok

"""
copy_vlan_attributes: copy prefix and link type from vlan to link
"""
def copy_vlan_attributes(vlan: str, vlan_data: Box, link: Box) -> None:
  if 'prefix' in vlan_data:
    link.prefix = vlan_data.prefix
  if not 'type' in link:
    link.type = vlan_data.get('type','lan')
  link.vlan_name = vlan

"""
set_link_vlan_prefix: copy link attributes from VLAN for access/native VLAN links

* We're assuming the attributes passed VLAN validity checks, so it's safe to
  use the collected v_attr data
* If there's access or native VLAN defined on the link, use it to set link attributes
"""

def set_link_vlan_prefix(link: Box, v_attr: Box, topology: Box) -> None:
  link_vlan_set: set = set()
  node_set: set = set()

  if 'access' in v_attr:
    link_vlan_set = v_attr.access.set
    node_set = v_attr.access.node_set
  elif 'native' in v_attr:
    link_vlan_set = v_attr.native.set
    node_set = v_attr.native.node_set

  if not link_vlan_set:
    return

  link_vlan = list(link_vlan_set)[0]                  # Got the access/native VLAN
  if link_vlan in topology.get('vlans',{}):
    copy_vlan_attributes(link_vlan,topology.vlans[link_vlan],link)
    return

  if not node_set:
    common.fatal(f'Cannot find the node using VLAN {link_vlan}\n... {link}')
    return

  copy_vlan_attributes(link_vlan,topology.nodes[list(node_set)[0]].vlans[link_vlan],link)

"""
get_vlan_data: Get VLAN data structure (node or topology)
"""
def get_vlan_data(vlan: str, node: Box, topology: Box) -> Box:
  return topology.vlans[vlan] if vlan in topology.get('vlans',{}) else node.vlans[vlan]

"""
update_vlan_neighbor_list: Build a VLAN-wide list of neighbors
"""
def update_vlan_neighbor_list(vlan: str, phy_if: Box, svi_if: Box, node: Box,topology: Box) -> None:
  vlan_data = get_vlan_data(vlan,node,topology)
  if not 'neighbors' in vlan_data:
    vlan_data.neighbors = []

  n_map = { data.node: data for data in vlan_data.neighbors }           # Build a list of known VLAN neighbors
  phy_n_list = phy_if.get('neighbors',[])                               # ... add interface neighbors not yet in the list
  vlan_data.neighbors.extend([n_data for n_data in phy_n_list if n_data.node not in n_map])

  if node.name in n_map:                                                # Is the current node in the list?
    n_map[node.name].ifname = svi_if.ifname                             # ... it is, fix the interface name
    for af in ('ipv4','ipv6'):
      if af in svi_if:
        n_map[node.name][af] = svi_if[af]
      else:
        n_map[node.name].pop(af,None)
  else:
    n_data = { 'ifname': svi_if.ifname, 'node': node.name }             # ... not yet, create neighbor data
    for af in ('ipv4','ipv6'):
      if af in svi_if:                                                  # ... copy SVI interface addresses to neighbor data
        n_data[af] = svi_if[af]
    vlan_data.neighbors.append(n_data)                                  # Add current node as a neighbor to VLAN neighbor list

"""
create_svi_interfaces: for every physical interface with access VLAN, create an SVI interface
"""
def create_svi_interfaces(node: Box, topology: Box) -> None:
  vlan_ifmap: dict = {}
  bridge_group = 0

  phy_ifattr = ['bridge','ifindex','ifname','linkindex','type','vlan']      # Physical interface attributes
  svi_skipattr = ['id','vni','prefix','pool']                               # VLAN attributes not copied into VLAN interface
  iflist_len = len(node.interfaces)
  for ifidx in range(0,iflist_len):
    ifdata = node.interfaces[ifidx]
    access_vlan = get_from_box(ifdata,'vlan.access')
    if not access_vlan:                                                     # No access VLAN on this interface?
      continue                                                              # ... good, move on

    if not access_vlan in node.vlans:                                       # Do we have VLAN defined in the node?
      node.vlans[access_vlan] = Box(topology.vlans[access_vlan])            # ... no, create a copy of the global definition
      if not node.vlans[access_vlan]:                                       # pragma: no cover -- we don't have a global definition? 
        common.fatal(                                                       # ... this should have been detected way earlier
          f'Unknown VLAN {access_vlan} used on node {node.name}','vlan')
        continue

    vlan_data = node.vlans[access_vlan]                                     # Slowly setting things up: VLAN data
    if not 'bridge_group' in vlan_data:                                     # ... bridge group in VLAN definition
      bridge_group = bridge_group + 1
      vlan_data.bridge_group = bridge_group
                                                                            # ... and SVI interface name
    svi_name = devices.get_device_attribute(node,'svi_name',topology.defaults)
    if not svi_name:                                                        # pragma: no cover -- hope we got device settings right ;)
      common.error(                                                         # SVI interfaces are not supported on this device
        f'Device {node.device} used by {node.name} does not support VLAN interfaces (access vlan {access_vlan})',
        common.IncorrectValue,
        'vlan')
      return

    if not access_vlan in vlan_ifmap:                                       # Do we need to create a SVI interface?
      skip_attr = list(phy_ifattr)                                          # Create a local copy of the attribute skip list
      if vlan_data.get('mode','') == 'bridge':                              # ... and skip IP addresses for bridging-only VLANs
        skip_attr.extend(['ipv4','ipv6'])
      vlan_ifdata = Box(                                                    # Copy non-physical interface attributes into SVI interface
        { k:v for k,v in ifdata.items() if k not in skip_attr },            # ... that will also give us IP addresses
        default_box=True,
        box_dots=True)
      vlan_ifdata.ifindex = node.interfaces[-1].ifindex + 1                 # Fill in the rest of interface data:
      vlan_ifdata.ifname = svi_name.format(                                 # ... ifindex, ifname, description
                              vlan=vlan_data.id,
                              bvi=vlan_data.bridge_group)
      vlan_ifdata.name = f'VLAN {access_vlan} ({vlan_data.id})'
      vlan_ifdata.virtual_interface = True                                  # Mark interface as virtual
      vlan_ifdata.neighbors = []                                            # No neighbors so far
                                                                            # Overwrite interface settings with VLAN settings
      vlan_ifdata = vlan_ifdata + { k:v for k,v in vlan_data.items() if k not in svi_skipattr }
      node.interfaces.append(vlan_ifdata)                                   # ... and add SVI interface to list of node interfaces
      vlan_ifmap[access_vlan] = vlan_ifdata
    else:
      vlan_ifdata = vlan_ifmap[access_vlan]

    update_vlan_neighbor_list(access_vlan,ifdata,vlan_ifdata,node,topology)

    for attr in list(ifdata.keys()):                                        # Clean up physical interface data
      if not attr in phy_ifattr:
        ifdata.pop(attr,None)

    ifdata.vlan.access_id = vlan_data.id                                    # Add VLAN ID to interface data to simplify config templates

"""
set_svi_neighbor_list: set SVI neighbor list from VLAN neighbor list
"""
def set_svi_neighbor_list(node: Box, topology: Box) -> None:
  for ifdata in node.interfaces:
    if 'vlan_name' in ifdata:
      vlan_data = get_vlan_data(ifdata.vlan_name,node,topology)
      if not 'host_count' in vlan_data:                                     # Calculate the number of hosts attached to the VLAN
        vlan_data.host_count = len([ n for n in vlan_data.neighbors if topology.nodes[n.node].get('role','') == 'host' ])

      if not 'role' in ifdata:                                              # If the interface has no 'role' copied from the link
        if len(vlan_data.neighbors) == vlan_data.host_count +1:             # ... and there's exactly one non-host attached to the VLAN
          ifdata.role = 'stub'                                              # ... then we have a stub link, mark it for IGP modules

      ifdata.neighbors = [ n for n in vlan_data.neighbors if n.node != node.name ]
      if ifdata.neighbors:
        if ' -> ' in ifdata.name:
          ifdata.name = ifdata.name.split(' -> ')[0]
        ifdata.name = ifdata.name + " -> [" + ",".join([ n.node for n in ifdata.neighbors]) + "]"

class VLAN(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    if get_from_box(topology,'vlan.mode'):
      if topology.vlan.mode not in vlan_mode_kwd:     # pragma: no cover
        common.error(
          f'Invalid global vlan.mode value {topology.vlan.mode}',
          common.IncorrectValue,
          'vlan')
        return

    populate_vlan_id_set(topology)

    if not 'vlans' in topology:
      return

    validate_vlan_attributes(topology,topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if 'vlans' in node:
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
    v_attr = Box({},default_box=True,box_dots=True)
    link_ok = check_link_vlan_attributes(link,link,v_attr,topology)                # Check link-level VLAN attributes

    for intf in link.interfaces:
      link_ok = link_ok and check_link_vlan_attributes(intf,link,v_attr,topology)  # Check interface VLAN attributes

    if not link_ok:
      return

    if not validate_link_vlan_attributes(link,v_attr,topology):
      return

    set_link_vlan_prefix(link,v_attr,topology)

  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'vlan' in n.get('module',[]):
        create_svi_interfaces(n,topology)

    for n in topology.nodes.values():
      set_svi_neighbor_list(n,topology)
