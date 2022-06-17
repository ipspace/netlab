#
# VRF module
#
import typing
from box import Box

from . import _Module,_routing,get_effective_module_attribute
from .. import common
from .. import data
from .. import addressing
from ..data import get_from_box
from ..augment import devices
from ..augment import links

# Global variables -- would love to be without them, but the alternatives
# are even messier
#
vlan_ids: Box
vlan_next: Box

# Static lists of keywords
#
vlan_mode_kwd: typing.Final[list] = [ 'bridge', 'irb', 'route' ]

vlan_link_attr: typing.Final[dict] = {
  'access': { 'type' : str, 'vlan': True, 'single': True },
  'native': { 'type' : str, 'vlan': True, 'single': True },
  'mode':   { 'type' : str },
  'trunk' : { 'type' : dict,'vlan': True }
}

phy_ifattr: typing.Final[list] = ['bridge','ifindex','parentindex','ifname','linkindex','type','vlan','mtu'] # Physical interface attributes
keep_subif_attr: typing.Final[list] = ['vlan','ifindex','ifname','type']    # Keep these attributes on VLAN subinterfaces

"""
init_global_vars: Initialize the VLAN ID pool
"""
def init_global_vars() -> None:
  global vlan_ids, vlan_next
  vlan_ids = Box({},default_box=True,box_dots=True)
  vlan_next = Box({},default_box=True,box_dots=True)

#
# build_vlan_id_set: given an object (topology or node), create a set of VLAN attributes (ID or VNI)
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

  vlan_ids[k].add(vlan_next[k])
  return vlan_next[k]

#
# routed_access_vlan: Given a link with access/native VLAN, check if all nodes on the link use routed VLAN
#
def routed_access_vlan(link: Box, topology: Box, vlan: str) -> bool:
  def_link  = get_from_box(link,'vlan.mode')
  def_vlan  = get_from_box(topology,f'vlans.{vlan}.mode')
  def_global = get_from_box(topology,'vlan.mode') or 'irb'

  #print(f'RAV: {link}')
  #print(f'RAV: vlan {vlan} def_mode {def_mode}')
  for intf in link.interfaces:
    mode = get_from_box(intf,'vlan.mode') or \
           def_link or \
           get_from_box(topology.nodes[intf.node],f'vlans.{vlan}.mode') or \
           get_from_box(topology.nodes[intf.node],'vlan.mode') or \
           def_vlan or \
           def_global or 'irb'
    if mode != 'route':
      return False

  #print(f'RAV: routed VLAN')
  return True

#
# interface_vlan_mode: Given an interface, a node, and topology, find interface VLAN mode
#
def interface_vlan_mode(intf: Box, node: Box, topology: Box) -> str:
  vlan = get_from_box(intf,'vlan.access') or get_from_box(intf,'vlan.native')
  if not vlan:
    return 'irb'

  return get_from_box(intf,'vlan.mode') or \
         get_from_box(node,f'vlans.{vlan}.mode') or \
         get_from_box(node,'vlan.mode') or \
         get_from_box(topology,f'vlans.{vlan}.mode') or \
         get_from_box(topology,'vlan.mode') or 'irb'

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

    if isinstance(obj.vlan[attr],dict):                           # Change empty VLAN keys into dictionaries
      for k in obj.vlan[attr].keys():
        if obj.vlan[attr][k] is None:
          obj.vlan[attr][k] = {}

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

  if 'native' in v_attr:                                          # Do we have a native VLAN defined on the link?
    if not set.intersection(v_attr.native.set,v_attr.trunk.set):  # Is it included in the VLAN trunk?
      common.error(
        f'Native VLAN {v_attr.native.list[0]} used on a link is not in the VLAN trunk definition\n... {link}',
        common.IncorrectValue,
        'vlan')
    else:
      for intf in link.interfaces:                                # Now check if every node using native VLAN has it in its trunk
        if 'vlan' in intf:                                        # VLAN attributes on interface?
                                                                  # Calculate effective node trunk and native VLAN data
          node_trunk = get_effective_module_attribute('vlan.trunk',intf=intf,link=link)
          node_native = get_effective_module_attribute('vlan.native',intf=intf,link=link)
          if node_native:                                         # Does this node use native VLAN?
            if not node_trunk:                                    # ... no trunk data for this node, cannot use native VLAN
              common.error(
                f'Node {intf.node} is using native VLAN without VLAN trunk\n... {link}',
                common.IncorrectValue,
                'vlan')
            elif not intf.vlan.native in node_trunk:              # ... native VLAN not in trunk, that's not valid
              common.error(
                f'Node {intf.node} is using native VLAN that is not defined in its VLAN trunk\n... {link}',
                common.IncorrectValue,
                'vlan')
          else:                                                   # There's native VLAN on this link, but not on this node
            if isinstance(node_trunk,Box):                        # ... trunk data should be a Box, but mypy doesn't know that ;)
              if v_attr.native.list[0] in node_trunk:             # ... if this node lists native VLAN in its trunk we have  problem
                common.error(
                  f'Native VLAN used on the link is in the VLAN trunk of node {intf.node}, but is not configured as native VLAN\n... {link}',
                  common.IncorrectValue,
                  'vlan')
                continue
              for af in ('ipv4','ipv6'):                          # Interface is not participating in native VLAN
                intf[af] = False                                  # ... make sure it's not connected to the native VLAN subnet
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
get_link_access_vlan: given v_attr data structure, find usable access or native vlan
"""
def get_link_access_vlan(v_attr: Box) -> typing.Optional[str]:
  if 'access' in v_attr:
    if v_attr.access.set:
      return list(v_attr.access.set)[0]

  if 'native' in v_attr:
    if v_attr.native.set:
      return list(v_attr.native.set)[0]

  return None

"""
fix_vlan_mode_attribute: Given an interface/link data structure, replace 'mode' with 'vlan.mode'
"""
def fix_vlan_mode_attribute(data: Box) -> None:
  if 'mode' in data:
    data.vlan.mode = data.mode
    data.pop('mode',None)


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
  elif 'trunk' in v_attr:
    if not 'role' in link and not 'prefix' in link:   # If the user set prefix or address pool leave it alone
      link.prefix = {}                                # ... otherwise we need no IP addressing on trunk links without a native VLAN
    return

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
create_vlan_links: Create virtual links for every VLAN in the VLAN trunk
"""
def create_vlan_links(link: Box, v_attr: Box, topology: Box) -> None:
  native_vlan = link.get('vlan_name',None)
  for vname in sorted(v_attr.trunk.set):
    if vname != native_vlan:           # Skip native VLAN
      link_data = Box(link.vlan.trunk[vname] or {},default_box=True,box_dots=True)
      link_data.linkindex = topology.links[-1].linkindex + 1
      link_data.parentindex = link.linkindex
      link_data.vlan.access = vname
      link_data.vlan_name = vname
      link_data.type = 'vlan_member'
      link_data.interfaces = []
      fix_vlan_mode_attribute(link_data)

      if vname in topology.get('vlans',{}):                 # We need an IP prefix for the VLAN link
        prefix = topology.vlans[vname].prefix               # Hopefully we can get it from the global VLAN pool

      for intf in link.interfaces:
        if 'vlan' in intf and vname in intf.vlan.get('trunk',{}):
          intf_data = Box(intf.vlan.trunk[vname] or {},default_box=True,box_dots=True)
          intf_data.node = intf.node
          if 'mode' in intf.vlan and not get_from_box(intf_data,'vlan.mode'):
            intf_data.vlan.mode = intf.vlan.mode            # vlan.mode is inherited from trunk dictionary or parent interface
          link_data.interfaces.append(intf_data)
          if not prefix:                                    # Still no usable IP prefix? Try to get it from the node VLAN pool
            if vname in topology.nodes[intf.node].get('vlans',{}):
              prefix = topology.node[intf.node].vlans[vname].prefix

      if routed_access_vlan(link_data,topology,vname):
        link_data.vlan.mode = 'route'
        for intf in link_data.interfaces:
          intf.vlan.mode = 'route'
      else:
        link_data.prefix = prefix

      topology.links.append(link_data)

"""
get_vlan_data: Get VLAN data structure (node or topology)
"""
def get_vlan_data(vlan: str, node: Box, topology: Box) -> typing.Optional[Box]:
  return get_from_box(topology,f'vlans.{vlan}') or get_from_box(node,f'vlans.{vlan}')

"""
update_vlan_neighbor_list: Build a VLAN-wide list of neighbors
"""
def update_vlan_neighbor_list(vlan: str, phy_if: Box, svi_if: Box, node: Box,topology: Box) -> None:
  vlan_data = get_vlan_data(vlan,node,topology)                         # Try to get global or node-level VLAN data
  if vlan_data is None:                                                 # ... and get out if there's none
    return

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
create_node_vlan: Create a local (node) copy of a VLAN used on an interface
"""
def create_node_vlan(node: Box, vlan: str, topology: Box) -> typing.Optional[Box]:
  if not vlan in node.vlans:                                        # Do we have VLAN defined in the node?
    node.vlans[vlan] = Box(topology.vlans[vlan])                    # ... no, create a copy of the global definition
    if not node.vlans[vlan]:                                        # pragma: no cover -- we don't have a global definition?
      common.fatal(                                                 # ... this should have been detected way earlier
        f'Unknown VLAN {vlan} used on node {node.name}','vlan')
      return None

  if not 'bridge_group' in node.vlans[vlan]:                        # Set bridge group in VLAN data
    if not node.vlan.max_bridge_group:                              # ... current counter is in node.vlan dictionary
      node.vlan.max_bridge_group = 1
    else:
      node.vlan.max_bridge_group = node.vlan.max_bridge_group + 1
    node.vlans[vlan].bridge_group = node.vlan.max_bridge_group

  return node.vlans[vlan]

"""
create_svi_interfaces: for every physical interface with access VLAN, create an SVI interface
"""

def create_svi_interfaces(node: Box, topology: Box) -> dict:
  global phy_ifattr
  skip_ifattr = list(phy_ifattr)
  skip_ifattr.extend(topology.defaults.providers.keys())

  vlan_ifmap: dict = {}

  svi_skipattr = ['id','vni','prefix','pool']                               # VLAN attributes not copied into VLAN interface
  iflist_len = len(node.interfaces)
  for ifidx in range(0,iflist_len):
    ifdata = node.interfaces[ifidx]
    access_vlan = get_from_box(ifdata,'vlan.access') or get_from_box(ifdata,'vlan.native')
    if not access_vlan:                                                     # No access VLAN on this interface?
      continue                                                              # ... good, move on

    routed_intf = interface_vlan_mode(ifdata,node,topology) == 'route'      # Identify routed VLAN interfaces
    vlan_subif  = routed_intf and ifdata.get('type','') == 'vlan_member'    # ... and VLAN-based subinterfaces

    vlan_data = create_node_vlan(node,access_vlan,topology)
    if vlan_data is None:                                                   # pragma: no-cover
      if vlan_subif:                                                        # We should never get here, but at least we can
        common.fatal(                                                       # scream before crashing
          f'Weird: cannot get VLAN data for VLAN {access_vlan} on node {node.name}, aborting')
      continue

    if routed_intf:                                                         # Routed VLAN access interface, turn it back into native interface
      for k in ('access','native'):                                         # ... remove access VLAN attributes
        ifdata.vlan.pop(k,None)

      if not ifdata.vlan:                                                   # ... and VLAN dictionary if there's nothing else left
        ifdata.pop('vlan',None)

      vlan_copy = { k:v for (k,v) in vlan_data.items() if not k in svi_skipattr and k != 'mode' }

      if vlan_subif:
        ifdata.vlan.mode = 'route'
        ifdata.vlan.access_id = vlan_data.id

      node.interfaces[ifidx] = vlan_copy + ifdata                           # Merge VLAN data with interface data
      continue                                                              # Move to next interface

    features = devices.get_device_features(node,topology.defaults)
    svi_name = features.vlan.svi_interface_name
    if not svi_name:                                                        # pragma: no cover -- hope we got device settings right ;)
      common.error(                                                         # SVI interfaces are not supported on this device
        f'Device {node.device} used by {node.name} does not support VLAN interfaces (access vlan {access_vlan})',
        common.IncorrectValue,
        'vlan')
      return vlan_ifmap

    if not access_vlan in vlan_ifmap:                                       # Do we need to create a SVI interface?
      skip_attr = list(skip_ifattr)                                         # Create a local copy of the attribute skip list
      vlan_mode = ifdata.vlan.get('mode','') or vlan_data.get('mode','')    # Get VLAN forwarding mode
      if vlan_mode == 'bridge':                                             # ... and skip IP addresses for bridging-only VLANs
        skip_attr.extend(['ipv4','ipv6'])
      vlan_ifdata = Box(                                                    # Copy non-physical interface attributes into SVI interface
        { k:v for k,v in ifdata.items() if k not in skip_attr },            # ... that will also give us IP addresses
        default_box=True,
        box_dots=True)
      if vlan_mode:                                                         # Set VLAN forwarding mode for completness' sake
        vlan_ifdata.vlan.mode = vlan_mode
      vlan_ifdata.ifindex = node.interfaces[-1].ifindex + 1                 # Fill in the rest of interface data:
      vlan_ifdata.ifname = svi_name.format(                                 # ... ifindex, ifname, description
                              vlan=vlan_data.id,
                              bvi=vlan_data.bridge_group,
                              ifname=ifdata.ifname)
      vlan_ifdata.name = f'VLAN {access_vlan} ({vlan_data.id})'
      vlan_ifdata.virtual_interface = True                                  # Mark interface as virtual
      vlan_ifdata.type = "svi"
      vlan_ifdata.neighbors = []                                            # No neighbors so far
                                                                            # Overwrite interface settings with VLAN settings
      vlan_ifdata = vlan_ifdata + { k:v for k,v in vlan_data.items() if k not in svi_skipattr }
      fix_vlan_mode_attribute(vlan_ifdata)
      node.interfaces.append(vlan_ifdata)                                   # ... and add SVI interface to list of node interfaces
      vlan_ifmap[access_vlan] = vlan_ifdata
    else:
      vlan_ifdata = vlan_ifmap[access_vlan]

    update_vlan_neighbor_list(access_vlan,ifdata,vlan_ifdata,node,topology)

    for attr in list(ifdata.keys()):                                        # Clean up physical interface data
      if not attr in skip_ifattr:
        ifdata.pop(attr,None)

    ifdata.vlan.access_id = vlan_data.id                                    # Add VLAN ID to interface data to simplify config templates

  return vlan_ifmap

"""
set_svi_neighbor_list: set SVI neighbor list from VLAN neighbor list
"""
def set_svi_neighbor_list(node: Box, topology: Box) -> None:
  for ifdata in node.interfaces:
    if 'vlan_name' in ifdata:
      vlan_data = get_vlan_data(ifdata.vlan_name,node,topology)             # Try to get global or local VLAN data
      if vlan_data is None:                                                 # Not found?
        continue                                                            # ... too bad

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

"""
map_trunk_vlans: build a list of VLAN IDs on trunk interfaces
"""
def map_trunk_vlans(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    trunk = get_from_box(intf,'vlan.trunk')
    if not trunk:
      continue

    vlan_list = []
    for vlan in trunk.keys():
      if not vlan in node.vlans:
        common.fatal(f'Internal error: VLAN {vlan} should be already defined on node {node.name}')
        break
      vlan_list.append(node.vlans[vlan].id)

    intf.vlan.trunk_id = vlan_list

"""
find_parent_interface: Find the parent interface of a VLAN member subinterface
"""
def find_parent_interface(intf: Box, node: Box, topology: Box) -> typing.Optional[Box]:
  link_list = [ l for l in topology.links if l.linkindex == intf.parentindex ]
  if not link_list:
    return None

  link = link_list[0]
  intf_list = [ intf for intf in link.interfaces if intf.node == node.name]
  if not intf_list:
    return None

  link_intf = intf_list[0]

  node_iflist = [ intf for intf in node.interfaces if intf.ifindex == link_intf.ifindex]
  if not node_iflist:
    return None

  return node_iflist[0]

"""
rename_vlan_subinterfaces: rename or remove interfaces created from VLAN pseudo-links
"""
def rename_vlan_subinterfaces(node: Box, topology: Box) -> None:
  global phy_ifattr
  skip_ifattr = list(phy_ifattr)
  skip_ifattr.extend(topology.defaults.providers.keys())

  features = devices.get_device_features(node,topology.defaults)
  if 'switch' in features.vlan.model:                             # No need for VLAN subinterfaces, remove non-routed vlan_member interfaces
    node.interfaces = [ intf for intf in node.interfaces \
                          if intf.type != 'vlan_member' or intf.vlan.get('mode','') == 'route' ]
    subif_name = features.vlan.routed_subif_name                  # Just in case: try to get interface name pattern for routed subinterface

  for intf in node.interfaces:                                    # Now loop over remaining vlan_member interfaces
    if intf.type != 'vlan_member':
      continue

    if not 'router' in features.vlan.model and not 'l3-switch' in features.vlan.model:
      #
      # The only way to get here is to have a routed VLAN in a VLAN trunk on a device that
      # does not support VLAN subinterfaces
      #
      common.error(
        f'Routed subinterfaces on VLAN trunks not supported on device type {node.device}\n... node {node.name} vlan {intf.vlan_name}',
        common.IncorrectValue,'vlan')
      continue

    subif_name = features.vlan.subif_name
    if not subif_name:                                            # pragma: no-cover -- hope we got device settings right
      common.fatal(
        f'Internal error: device {node.device} acts as a VLAN-capable {features.vlan.model} but does not have subinterface name template')
      continue

    parent_intf = find_parent_interface(intf,node,topology)
    if parent_intf is None:
      common.fatal(f'Internal error: cannot find parent interface for {intf} in node {node.name}')
      return

    if 'subif_index' in parent_intf:
      parent_intf.subif_index = parent_intf.subif_index + 1
    else:
      parent_intf.subif_index = features.vlan.first_subif_id or 1

    ifname_data = parent_intf + intf                                  # Add parent interface data to subinterface data
    ifname_data.ifname = parent_intf.ifname                           # ... making sure ifname is coming from parent interface

    old_intf = Box({ 'ifname': intf.ifname })                         # Create a fake interface with old interface name
    intf.ifname = subif_name.format(**ifname_data)
    intf.parent_ifindex = parent_intf.ifindex
    intf.parent_ifname = parent_intf.ifname
    intf.virtual_interface = True
    if 'vlan_name' in intf:
      update_vlan_neighbor_list(intf.vlan_name,old_intf,intf,node,topology)

    for attr in skip_ifattr:
      if attr in intf and not attr in keep_subif_attr:
        intf.pop(attr,None)

    if intf.vlan.access_id in parent_intf.vlan.get('trunk_id',[]):    # Remove subinterface VLAN from parent interface trunk list
      parent_intf.vlan.trunk_id = [ vlan for vlan in parent_intf.vlan.trunk_id if vlan != intf.vlan.access_id ]
      if not parent_intf.vlan.trunk_id:                               # Nothing left?
        parent_intf.vlan.pop('trunk_id',None)                         # ... remove all trunk-related attributes from parent interface
        parent_intf.vlan.pop('trunk',None)
        if not parent_intf.vlan:                                      # And remove the VLAN dictionary if it's no longer needed
          parent_intf.pop('vlan',None)

  # Final check: mixed bridged/routed trunks
  #
  # We can skip this check if the device supports mixed routed/bridged trunks or if it
  # uses VLAN subinterfaces to implement VLANs.
  #
  if features.vlan.mixed_trunk:
    return

  err_ifmap = {}
  for intf in node.interfaces:
    if not intf.get('parent_ifindex') or intf.type != 'vlan_member':  # Skip everything that is not a VLAN subinterface
      continue

    parent_intf_list = [ x for x in node.interfaces if x.ifindex == intf.parent_ifindex ]
    if not parent_intf_list:
      common.fatal(f'Internal error: cannot find parent interface for {intf} in node {node.name}')
      return

    parent_intf = parent_intf_list[0]
    if parent_intf is None \
         or get_from_box(parent_intf,'vlan.trunk_id') is None:        # No VLAN trunk left on the parent interface?
      continue                                                        # ... cool, we're done

    if not parent_intf.ifindex in err_ifmap:                          # We have a problem. Do we have to generate an error?
      common.error(
        f'Device type {node.device} does not support mixed bridged/routed VLAN trunks\n'+ \
        f'... node {node.name} interface {parent_intf.ifname}: {parent_intf.name}',
        common.IncorrectValue,
        'vlan')
    err_ifmap[parent_intf.ifindex] = True

"""
cleanup_vlan_name -- remove internal 'vlan_name' attribute from links and interfaces
"""

def cleanup_vlan_name(topology: Box) -> None:
  if 'links' in topology:
    for l in topology.links:
      if 'vlan_name' in l:
        l.pop('vlan_name',None)

  for n in topology.nodes.values():
    for intf in n.interfaces:
      if 'vlan_name' in intf:
        intf.pop('vlan_name',None)

class VLAN(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    init_global_vars()
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
        if node.vlans[vname] is None:
          node.vlans[vname] = {}
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
    if link.get('type','') == 'vlan_member':                                      # Skip VLAN member links, we've been there...
      return

    v_attr = Box({},default_box=True,box_dots=True)
    link_ok = check_link_vlan_attributes(link,link,v_attr,topology)               # Check link-level VLAN attributes

    for intf in link.interfaces:
      link_ok = link_ok and check_link_vlan_attributes(intf,link,v_attr,topology) # Check interface VLAN attributes

    if not link_ok:
      return

    if not validate_link_vlan_attributes(link,v_attr,topology):
      return

    svi_skipattr = ['id','vni','mode','pool','prefix']                             # VLAN attributes not copied into link data
    link_vlan = get_link_access_vlan(v_attr)
    routed_vlan = False
    if not link_vlan is None:
      routed_vlan = routed_access_vlan(link,topology,link_vlan)
      vlan_data = get_from_box(topology,f'vlans.{link_vlan}')                      # Get global VLAN data
      if isinstance(vlan_data,Box):
        vlan_data = Box({ k:v for (k,v) in vlan_data.items() \
                                if k not in svi_skipattr })                       # Remove VLAN-specific data
        fix_vlan_mode_attribute(vlan_data)                                        # ... and turn mode into vlan.mode
        for (k,v) in vlan_data.items():                                           # Now add the rest to link data
          if not k in link:                                                       # ... have to do the deep merge manually as
            link[k] = v                                                           # ... we cannot just replace link data structure
          elif isinstance(link[k],Box) and isinstance(vlan_data[k],Box):
            link[k] = vlan_data[k] + link[k]

    if routed_vlan:
      link.vlan.mode = 'route'
    else:
      set_link_vlan_prefix(link,v_attr,topology)

    # Merge link VLAN attributes into interface VLAN attributes to make subsequent steps easier
    if 'vlan' in link:
      for intf in link.interfaces:
        if 'vlan' in topology.nodes[intf.node].get('module',[]):
          intf.vlan = link.vlan + intf.vlan

    if 'trunk' in v_attr:
      create_vlan_links(link,v_attr,topology)

  def module_post_transform(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if 'vlan' in n.get('module',[]):
        vlan_ifmap = create_svi_interfaces(n,topology)
        map_trunk_vlans(n,topology)
        rename_vlan_subinterfaces(n,topology)

    for n in topology.nodes.values():
      set_svi_neighbor_list(n,topology)

    topology.links = [ link for link in topology.links if link.type != 'vlan_member' ]

    cleanup_vlan_name(topology)
