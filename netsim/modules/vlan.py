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
validate_link_vlan_attributes: limited implementation dealing with access VLANs

Make sure that:
* nobody is using 'trunk','native' or 'mode' attributes
* access VLAN is specified if the VLAN attribute is used
* access VLAN is not specified on a link and on an interface
"""
def validate_link_vlan_attributes(obj: Box,link: Box) -> bool:
  if not 'vlan' in obj:
    return True

  if not isinstance(obj.vlan,dict):
    common.error(f'vlan link attribute must be a dictionary\n... {link}',common.IncorrectValue,'vlan')
    return False

  for attr in ('trunk','native'):
    if attr in obj.vlan:
      common.error(
        f'VLAN link/interface attribute {attr} is not yet supported',
        common.IncorrectValue,
        'vlan')
      return False

  if not 'access' in obj.vlan:
    common.error(
      f"You must specify access VLAN when using 'vlan' attribute on a link/interface\n... {link}",
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
def copy_vlan_attributes(vlan: str, vlan_data: Box, link: Box) -> None:
  if 'prefix' in vlan_data:
    link.prefix = vlan_data.prefix
  if not 'type' in link:
    link.type = vlan_data.get('type','lan')
  link.vlan_name = vlan

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
    copy_vlan_attributes(link.vlan.access,topology.vlans[link.vlan.access],link)
    return

  # No link-level access VLAN, build a list of interface access VLANs
  vlan_list = [ get_from_box(intf,'vlan.access') for intf in link.interfaces ]      # Collect all vlan.access settings
  vlan_list = [ vlan for vlan in vlan_list if vlan ]                                # ... and remove the empty ones
  if not vlan_list:                                   # No interface access VLAN? We're done, let's get out of here
    return

  if len(set(vlan_list)) > 1:                         # Oh my, more than one access VLAN. That can't be right
    common.error(
      f'Cannot use more than one access VLAN per link, found {vlan_list}\n...{link}',
      common.IncorrectValue,
      'vlan')
    return

  link_vlan = str(vlan_list[0])                       # All interface access VLANs are the same, take the first one
  if link_vlan in topology.get('vlans',{}):           # Are we dealing with a global access VLAN?
    copy_vlan_attributes(link_vlan,topology.vlans[link_vlan],link)
  else:
    if len(vlan_list) > 1:                             # Access VLAN defined on more than one interface?
      common.error(
        f'Access VLAN {link_vlan} used by more than one node attached to a link must be a global VLAN\n... {link}',
        common.IncorrectValue,
        'vlan')
      return

    # Find the node using the access VLAN
    node = next(intf.node for intf in link.interfaces if get_from_box(intf,'vlan.access') == link_vlan)

    # Hope the VLAN is defined within the node, otherwise we're truly lost
    if link_vlan in topology.nodes[node].get('vlans',{}):
      copy_vlan_attributes(link_vlan,topology.nodes[node].vlans[link_vlan],link)
    else:
      common.error(
        f'Access VLAN {link_vlan} used by node {node} should be defined globally or within the node\n... {link}',
        common.IncorrectValue,
        'vlan')

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

    populate_vlan_id_set(topology)
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
    if not validate_link_vlan_attributes(link,link):                    # Check link-level VLAN attributes
      return

    link_ok = True
    for intf in link.interfaces:
      link_ok = link_ok and validate_link_vlan_attributes(intf,link)    # Check interface VLAN attributes

    if not link_ok:
      return

    set_link_vlan_prefix(link,topology)

  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'vlan' in n.get('module',[]):
        create_svi_interfaces(n,topology)

    for n in topology.nodes.values():
      set_svi_neighbor_list(n,topology)
