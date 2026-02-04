'''
Add group support. This module handles group-related data structures and
data transformation. The end result is a dictionary of groups in 'groups'
top-level element. That dictionary is merged from global- and node-level parameters
'''

import copy
import fnmatch
import re
import typing

from box import Box

from .. import data, modules
from ..data import get_box
from ..data.types import must_be_dict, must_be_id, must_be_list, transform_asdot
from ..data.validate import get_object_attributes, validate_attributes
from ..modules import bgp, propagate_global_modules
from ..utils import log

'''
Return computed members of special-purpose node group ('all' or device)
'''
def special_node_group_members(group: str, topology: Box) -> typing.Optional[list]:
  if group == 'all':
    return list(topology.nodes)

  if group in topology.defaults.devices:
    return [ node for node,ndata in topology.nodes.items() if ndata.get('device',None) == group ]

  return None

'''
Return members of the specified group. Recurse through child groups if needed
'''
def group_members(topology: Box, group: str, grp_type: str = 'node', count: int = 0) -> list:
  members: typing.List[str] = []
  if not group in topology.groups:  # pragma: no cover (just-in case catch, impossible to get here)
    log.error(
      f'Internal error: unknown group {group}',
      log.IncorrectValue,
      'groups')
    return []

  if count > 99:                    # pragma: no cover (impossible to get here, recursive groups are checked elsewhere)
    log.fatal(
      'Recursive group definition, aborting',
      module='groups',
      header=True)

  gdata = topology.groups[group]
  g_type = gdata.get('type','node')
  if g_type != grp_type:
    return []

  if g_type == 'node':
    sg_members = special_node_group_members(group,topology)
    if not sg_members is None:
      return sg_members

  for m in gdata.get('members',[]):
    m_ns = grp_type + 's'
    if m in topology[m_ns]:
      members = members + [ m ]
    if m in topology.groups:
      members = members + group_members(topology,m,grp_type,count + 1)

  return members

'''
Check validity of 'groups' data structure

* groups -- the group data (topology- or default groups)
* topology -- top-level topology (have to pass it to get attributes from fixed location)
* prune_members -- remove non-existent group members (used for default groups)

The checks are implemented in two functions:

* check_group_data_sanity: called very early in the transformation process to do basic sanity
  checks needed before we can auto-create group members (if required)
* check_group-data_structure: called later when we already known topology-wide modules
  and can perform full node attribute validation
'''
def check_group_data_sanity(
      topology: Box,
      parent_path: typing.Optional[str] = '') -> bool:

  parent = topology.get(parent_path) if parent_path else topology
  grp_namespace = f'{parent_path} ' if parent_path else ''

  if must_be_dict(parent,'groups',parent_path,create_empty=True,module='topology') is None:
    return False

  '''
  Transform group-as-list into group-as-dictionary
  '''
  for grp in parent.groups.keys():
    if grp.startswith('_'):                       # Skip stuff starting with underscore
      continue                                    # ... could be system settings

    gpath = f'{parent_path or "topology"}.groups.{grp}'
    if parent.groups[grp] is None:
      log.error(
        f"Definition of {grp_namespace}group '{grp}' must be a dictionary",
        log.IncorrectType,
        'groups')
      return False

    if isinstance(parent.groups[grp],list):
      parent.groups[grp] = { 'members': parent.groups[grp] }

    if grp in topology.get('nodes',{}):
      log.error(
        f"{grp_namespace}group '{grp}' is also a node name. I can't deal with that level of confusion",
        log.IncorrectValue,
        'groups')
      return False

    if 'members' in parent.groups[grp]:
      if must_be_list(parent.groups[grp],'members',gpath,create_empty=False,module='groups') is None:
        return False

  return True

def group_re_match(m_expr: str, names: list) -> list:
  pattern = re.compile(m_expr[1:])
  return [ member for member in names if pattern.fullmatch(member) ]

"""
Expand the regular expressions or globs in the list of group members

Most of the function is just error checking and reporting, there's very little
actual work done here
"""
def expand_group_members(
      g_members: list,                # Members of the current group that have to be checked/expanded
      g_objects: Box,                 # Parent objects (nodes, VLANs, VRFs)
      g_list: list,                   # List of group names (to check hierarchical groups)
      g_name: str,                    # The name of the current group (needed for error messages)
      g_type: str,                    # Group type (node/vlan/vrf)
      g_prune: bool = False) -> list: # Prune non-existent group members (used in default groups)

  members: typing.List[str] = []
  g_names: typing.List[str] = []
  for m_id in g_members:
    if not isinstance(m_id,str):
      log.error(f'Member {m_id} of {g_type} group {g_name} is not a string',log.IncorrectType,module='groups')
      continue

    # Simple case: the member belongs to the group objects
    if m_id in g_objects or m_id in g_list:
      if m_id not in members:
        members.append(m_id)

    # Regular expression, identified by a string starting with ~
    elif m_id.startswith('~'):
      if not g_names:                             # Caching group object names just in case we're dealing
        g_names = list(g_objects)                 # ... with a humongous topology
      try:
        g_match = group_re_match(m_id,g_names)
      except Exception as ex:
        log.error(                                # Regex matching failed for some reason
          f'Invalid regular expression {m_id} used in {g_type} group {g_name}',
          more_data=str(ex),
          category=log.IncorrectValue,
          module='groups')
        continue
      if not g_match:                             # ... or we had no matches
        log.error(
          f'Regular expression {m_id} used in {g_type} group {g_name} does not match anything',
          category=log.IncorrectType,
          module='groups')
        continue

      # All good, add new re-matched members
      members += [ m for m in g_match if m not in members ]
      continue

    elif re.search('[\\[\\].*?!]',m_id):            # Using regexp to identify a potential glob pattern
      if not g_names:                             # Again: get a list of object names when first needed
        g_names = list(g_objects)
      try:
        g_match = fnmatch.filter(g_names,m_id)
      except Exception as ex:
        log.error(                                # Regex matching failed for some reason
          f'Invalid wildcard expression {m_id} used in {g_type} group {g_name}',
          more_data=str(ex),
          category=log.IncorrectValue,
          module='groups')
        continue
      if not g_match:
        log.error(
          f'Wildcard expression {m_id} used in {g_type} group {g_name} does not match anything',
          category=log.IncorrectType,
          module='groups')
        continue

      # All good, add new wildcard-matched members
      members += [ m for m in g_match if m not in members ]

    elif not g_prune:
      log.error(
        f'Member {m_id} of group {g_name} is not a valid {g_type} or group name',
        category=log.IncorrectValue,
        module='groups')

  return members

def check_group_data_structure(
      topology: Box,
      parent_path: typing.Optional[str] = '',
      prune_members: bool = False) -> None:

  parent = topology.get(parent_path) if parent_path else topology
  grp_namespace = f'{parent_path} ' if parent_path else ''
  reserved_names = list(topology.defaults.devices) + ['all']

  '''
  Sanity checks on global group data
  '''

  list_of_modules = modules.list_of_modules(topology)
  group_names = list(parent.groups)

  for grp,gdata in parent.groups.items():
    if grp.startswith('_'):                       # Skip stuff starting with underscore
      continue                                    # ... could be system settings

    must_be_id(parent=None,key=grp,path=f'NOATTR:group name {grp}',module='groups')

    gpath = f'{parent_path or "topology"}.groups'
    if must_be_dict(parent.groups,grp,gpath,create_empty=True,module='groups') is None:
      continue

    gpath=f'{gpath}.{grp}'
    g_type = gdata.get('type','node')
    gt_values = ['node','vlan','vrf']
    g_objects = topology.get(f'{g_type}s',{})
    if g_type not in gt_values:
      log.error(
        f"Invalid group type for group {grp}; can be {','.join(gt_values)}",
        category=log.IncorrectType,
        module='groups')

    g_namespace = [ f'{g_type}_group' ]
    g_namespace.extend(topology.defaults.attributes[g_namespace[0]].get('_namespace',[]))

    if not 'members' in gdata:
      gdata.members = []

    if grp in reserved_names and gdata.members:
      log.error(
        text=f'{grp_namespace}group "{grp}" should not have explicit members',
        more_hints='Device names or "all" cannot be used as names for user-defined groups',
        category=log.IncorrectValue,
        module='groups')
    if grp in topology.defaults.devices and 'device' in gdata:
      log.error(
        text=f'Trying to change the device to {gdata.device} in device group {grp} is ridiculous',
        category=log.IncorrectAttr,
        module='groups')

    must_be_list(gdata,'module',gpath,create_empty=False,module='groups',valid_values=sorted(list_of_modules))

    if log.pending_errors():                 # If we already found errors
      continue                               # ... then the group data structures are not safe to work on

    if must_be_list(gdata,'members',gpath,create_empty=False,module='groups') is None:
      continue

    gdata.members = expand_group_members(
                      g_members=gdata.members,
                      g_objects=g_objects,
                      g_list=group_names,
                      g_name=grp,
                      g_type=g_type,
                      g_prune=prune_members)

def validate_group_data(
      topology: Box,
      parent_path: typing.Optional[str] = '') -> None:

  parent = topology.get(parent_path) if parent_path else topology
  grp_namespace = f'{parent_path} ' if parent_path else ''

  if 'groups' not in parent:
    return

  # Allow provider-, tool-, and output- specific node attributes
  extra = get_object_attributes(topology.defaults.attributes.node_extra_ns,topology)

  for grp,gdata in parent.groups.items():
    if grp.startswith('_'):                       # Skip stuff starting with underscore
      continue                                    # ... could be system settings

    g_type = gdata.get('type','node')
    gpath = f'{parent_path or "topology"}.groups.{grp}'
    g_namespace = [ f'{g_type}_group' ]
    g_namespace.extend(topology.defaults.attributes[g_namespace[0]].get('_namespace',[]))
    group_attr = get_box(topology.defaults.attributes[g_namespace[0]])
    group_attr._default_group = 'str'       # We have to fake internal attributes, otherwise they're copied into node_data

    g_modules = gdata.get('module',[])
    if g_modules:                           # Modules specified in the group -- we know what these nodes will use
      gm_source = 'group'
    else:
      gm_source = 'topology'
      g_modules = topology.get('module',[])

    validate_attributes(
      data=gdata,
      topology=topology,
      data_path=gpath,
      data_name=g_namespace[0],
      attr_list=g_namespace,
      module='groups',
      modules=g_modules,
      module_source=gm_source,
      ignored=['_','netlab_','ansible_'],   # Ignore attributes starting with _, netlab_ or ansible_
      extra_attributes=extra)               # Allow provider- and tool-specific settings (not checked at the moment)

    # Validate node_data attributes (if any)
    if 'node_data' in gdata and g_type == 'node':
      log.warning(
        text=f'Group {grp} uses an obsolete attribute node_data. Migrate node parameters into group definition',
        flag='groups.node_data')

      validate_attributes(
        data=gdata.node_data,
        topology=topology,
        data_path=f'{gpath}.node_data',
        data_name='node',
        attr_list=[ 'node' ],
        module='groups',
        modules=g_modules,
        module_source=gm_source,
        ignored=['_','netlab_','ansible_'],  # Ignore attributes starting with _, netlab_ or ansible_
        extra_attributes=extra)              # Allow provider- and tool-specific settings (not checked at the moment)

      for k in ('module','device'):          # Check that the 'module' or 'device' attributes are not in node_data
        if k in gdata.node_data:
          log.error(
            f'Cannot use attribute {k} in node_data in {grp_namespace}group {grp}, set it as a group attribute',
            log.IncorrectValue,
            'groups')

    if log.pending_errors():                 # If we already found errors
      continue                               # ... then the group data structures are not safe to work on

    for k in list(gdata.keys()):             # Then move (validated) group node attributes into node_data
      if k in group_attr:
        continue
      gdata.node_data[k] = gdata[k]
      gdata.pop(k,None)


'''
Auto-create group members

Inputs:
* parent object (topology or defaults)
* topology (needed to add nodes)
* Global auto-create setting (set to 'False' for default groups)
'''

def auto_create_members(
      parent: Box,
      topology: Box,
      default_create: bool) -> None:

  if not 'groups' in parent:                      # Parent has no groups, what are we doing here?
    return

  for gname,gdata in parent.groups.items():       # Iterate over groups
    if gname.startswith('_'):                     # Skip stuff starting with '_' (could be global settings)
      continue

    if not 'members' in gdata:                    # Does the current group have members?
      continue                                    # ... nope, nothing to create

    # _auto_create could be set on the group or in global settings
    #
    if not gdata.get('_auto_create',False) and not default_create:
      continue                                    # No auto-create for this group, move on

    for n in gdata.members:                       # Iterate over group members
      #
      # Do not create nodes if the group member is another group
      if n in topology.get('groups',{}) or n in topology.get('defaults.groups',{}):
        continue

      obj_ns = gdata.get('type','node') + 's'

      if n in topology[obj_ns]:                   # Skip if the member is already a known object
        continue

      if obj_ns == 'nodes':                       # For auto-created nodes...
        topology[obj_ns][n].name = n              # ... create an empty node data structure
        topology[obj_ns][n].interfaces = []       # ... with an empty interface list
      else:
        topology[obj_ns][n] = {}                  # For all others, create a placeholder object
  
'''
Add node-level group settings to global groups
'''
def add_node_to_group(node: str, group: str, topology: Box) -> None:
  g_data = topology.groups[group]
  if g_data.get('type','node') != 'node':
    log.error(
      f"Cannot add node {node} to non-node group {group}",
      category=log.IncorrectType,
      module='groups')

  data.append_to_list(g_data,'members',node)

def add_node_level_groups(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if not 'group' in n:
      continue

    if must_be_list(n,'group',f'nodes.{name}'):
      for grpname in n.group:
        add_node_to_group(name,grpname,topology)

'''
Check recursive group definitions
'''

def check_recursive_chain(topology: Box, chain: list, group: str) -> typing.Optional[list]:
  if not group in topology.groups: # pragma: no cover (if we ever get here we're seriously messed up)
    log.fatal(
      'Internal error: unknown group in check_recursive_chain')
    return None

  chain = chain + [ group ]
  for m in topology.groups[group].members:
    if m in chain:
      chain = chain + [ m ]
      log.error(f'Recursive group definition chain {chain}', log.IncorrectValue, 'groups')
      return chain
    if m in topology.groups:
      if check_recursive_chain(topology,chain,m):
        return chain

  return None

def check_recursive_groups(topology : Box) -> None:
  for gname in topology.groups.keys():
    if gname.startswith('_'):                  # Skip settings starting with underscore
      continue
    if check_recursive_chain(topology,[],gname):
      return

def reverse_topsort(topology: Box) -> list:
  group_copy = get_box(topology.groups)        # Make a copy of the group dictionary
  sort_list: typing.List[str] = []

  for g in list(group_copy.keys()):            # Clean up the group data structure
    if g.startswith('_'):                      # Removing everything starting with underscore
      group_copy.pop(g,None)                   # ... those are settings, not groups

  while group_copy:                            # Keep iterating until we got all groups in order
    for g in sorted(group_copy.keys()):        # Iterate over remaining groups
      OK_to_add = True                         # ... sort them by name to have consistent results
      for m in group_copy[g].members:          # Now go check the group members
        if m in group_copy:                    # ... if a member of this group is still in groups we're not yet ready
          OK_to_add = False                    # ... to add it to sorted list
      if OK_to_add:                            # Have all child groups already been removed from the group dictionary?
        sort_list = sort_list + [ g ]          # ... if so, we're good to go, add current group to sorted list
        group_copy.pop(g)                      # ... and remove it from dictionary of remaining groups

  return sort_list

'''
Copy group-level module or device setting into node data
'''
def copy_group_device_module(topology: Box) -> None:
  sorted_groups = reverse_topsort(topology)
  for grp in sorted_groups:                                 # First, set the device type
    gdata = topology.groups[grp]
    if not 'device' in gdata:
      continue                                              # This group is not interesting, move on

    if log.debug_active('groups'):
      print(f'Setting device for group {grp}: {gdata.device}')
    g_members = group_members(topology,grp)
    if not g_members and not gdata.get('_default_group',False):
      log.error(
        f'Cannot use "device" attribute in group {grp} that has no direct or indirect members',
        log.IncorrectValue,
        'groups')
      continue

    for name in g_members:                                  # Iterate over group members
      if not name in topology.nodes:                        # Member not a node? Weird, move on...
        continue

      ndata = topology.nodes[name]
      if 'device' not in ndata:                             # Copy device from group data to node data
        ndata.device = gdata.device
        if log.debug_active('groups'):
          print(f'... setting {name}.device to {gdata.device}')

  for grp in sorted_groups:                                 # Next, augment device modules
    gdata = topology.groups[grp]                            # We have to do this after augmenting devices
                                                            # ... because modules could be specified on a device group
    if 'module' not in gdata:                               # No module specified on this group
      continue                                              # ... move on

    if log.debug_active('groups'):
      print(f'Setting module for group {grp}: {gdata.module}')
    g_members = group_members(topology,grp)
    if not g_members and not gdata.get('_default_group',False):
      log.error(
        f'Cannot use "module" attribute in group {grp} that has no direct or indirect members',
        log.IncorrectValue,
        'groups')
      continue

    for name in g_members:                                  # Iterate over group members
      if not name in topology.nodes:                        # Member not a node? Move on...
        continue

      ndata = topology.nodes[name]                          # Get node data
      if 'module' not in ndata:                             # Group can set module(s) to empty, so we have to
        ndata.module = []                                   # ... start with an empty list

      if not isinstance(ndata.module,list):                 # We'll let someone else deal with incorrect
        continue                                            # ... ndata.module data type

      for m in gdata.module:                                # ... iterate over group modules
        data.append_to_list(ndata,'module',m)               # ... and append group modules to node.module list

      if log.debug_active('groups'):
        print(f'... adding module {gdata.module} to {name}. Node modules now {ndata.module}')

'''
Copy node data from group into group members
'''
def copy_group_node_data(topology: Box,pfx: str) -> None:
  topo_modules = topology.get('module',[])                            # Get list of default list of modules
  for grp in reverse_topsort(topology):
    if not grp.startswith(pfx):                                       # Skip groups that don't match the current prefix (ex: BGP autogroups)
      continue
    gdata = topology.groups[grp]
    if not 'node_data' in gdata:                                      # No group data, skip
      continue

    g_type = gdata.get('type','node')
    g_members = group_members(topology,grp,g_type)                    # Get recursive list of members
    if log.debug_active('groups'):
      print(f'copy node data {grp}: {gdata.node_data}')

    g_ns = g_type + 's'                                               # Get the target object dictionary
    for name in g_members:                                            # Iterate over group members
      if not name in topology[g_ns]:                                  # Unknown member, skip it
        continue                                                      # ... should have been detected earlier

      if log.debug_active('groups'):
        print(f'... merging {g_type} data with {name}')
      merge_data = copy.deepcopy(gdata.node_data)
      if g_type == 'node' and 'module' in topology.nodes[name]:
        for m in topo_modules:
          if not m in topology.nodes[name].module:
            merge_data.pop(m,None)

      if topology[g_ns][name] is None:                                # We're early in data processing, some objects
        topology[g_ns][name] = {}                                     # ... might not have been initialized
      if isinstance(topology[g_ns][name],Box):                        # If the object is a box
        topology[g_ns][name] = merge_data + topology[g_ns][name]      # ... merge group data with it

'''
Export node_data from groups to topology

Used to create module-specific data structures in pre_transform hook before the
node data is populated from groups.node_data

Inputs:
* data structure name ('vrfs' or 'vlans')
* module name ('vrf' or 'vlan') -- used in error messages
* copy_keys: attributes that should be copied to topology-level data structure
* unique_keys: attributes that must be unique (set to copy_keys when empty)
'''
def export_group_node_data(
      topology: Box,
      key: str,
      module: str,
      copy_keys: typing.List[str] = [],
      unique_keys: typing.List[str] = []) -> None:

  if not unique_keys:
    unique_keys = copy_keys
  for gname,gdata in topology.groups.items():
    if gname.startswith('_'):                                         # Skip groups starting with '_'
      continue                                                        # ... those are group settings
    #
    # Find groups with node_data dictionaries
    # and check that the key within node_data dictionary we're interested in is also a dictionary
    #
    if must_be_dict(gdata,f'node_data.{key}',f'groups.{gname}',module=module,create_empty=False):
      for obj_name in list(gdata.node_data[key].keys()):              # Iterate over VLANs/VRFs within the group
        if gdata.node_data[key][obj_name] is None:                    # ... replace None values with
          gdata.node_data[key][obj_name] = {}                         # ... empty dictionaries
        obj_data =  gdata.node_data[key][obj_name]                    # Now get the data to work with
        if not obj_name in topology[key] or topology[key][obj_name] is None:
          topology[key][obj_name] = {}                                # Make sure global object is also a dictionary
        for attr in unique_keys:                                      # Check whether we have an overlap in unique keys
          if attr in topology[key][obj_name] and attr in obj_data and \
             topology[key][obj_name][attr] != obj_data[attr]:         # Unique key present on both ends and not equal
            log.error(
              f'Cannot redefine {key} attribute {attr} for {key}.{obj_name} from node_data in group {gname}',
              log.IncorrectValue,
              module)
        for attr in copy_keys:                                        # Finally, copy missing values from group to global object
          if attr in obj_data and attr not in topology[key][obj_name]:
            topology[key][obj_name][attr] = obj_data[attr]

#
# create_bgp_autogroups -- create BGP AS groups
#

def create_bgp_autogroups(topology: Box) -> None:
  g_module = topology.get('module',[])                          # Global list of modules, could be invalid
  if not isinstance(g_module,list):                             # Won't deal with incorrectly formatted 'module' attribute here
    g_module = []                                               # ... just assume it's an empty list
  g_bgpas = data.get_global_parameter(topology,'bgp.as')        # Try to get the global BGP AS
  err_list = []

  for gname,gdata in topology.groups.items():                   # Sanity check: BGP autogroups should not have static members
    if re.match('as\\d+$',gname):
      if gdata.get('members',None):                             # Well, it's OK to have an empty list of members ;)
        log.error(
          f'BGP AS group {gname} should not have static members',
          log.IncorrectValue,
          'groups')

  for n_name,n_data in topology.nodes.items():                  # Now iterate over nodes
    #
    # Get node or global module (global modules haven't been propagated yet) taking into account
    # whether the global modules will be propagated into the node
    #
    g_propagate = propagate_global_modules(n_data,topology)
    n_module = n_data.get('module',g_module if g_propagate else [])
    if not isinstance(n_module,list):                           # Node list of modules is insane, someone else will complain
      continue

    if not 'bgp' in n_module:                                   # Looks like this node does not care about BGP
      continue

    try:
      n_bgpas = n_data.get('bgp.as',g_bgpas)                    # Get node-level or global BGP AS
      if not data.is_true_int(n_bgpas):                         # ... if it's not int, it might be as.dot
        n_bgpas = transform_asdot(n_bgpas)
    except:
      n_bgpas = 0

    if not n_bgpas:
      continue

    grpname = f"as{n_bgpas}"                                    # BGP auto-group name
    if grpname in topology.nodes:
      if grpname not in err_list:
        log.error(
          f"Cannot create group '{grpname}' for BGP AS {n_bgpas}, node {grpname} already exists",
          category=log.IncorrectValue,
          module='groups')
      err_list.append(grpname)

    if not 'members' in topology.groups[grpname]:               # Set members of a new group to an empty list
      topology.groups[grpname].members = []                     # ... because we're using Box this also creates an empty group dict

    topology.groups[grpname].members.append(n_name)             # ... and append the node to AS group

  if err_list:
    log.exit_on_error()

"""
precheck_groups:

* Check the baseline group data structure sanity
* Auto-creates group members

This function is called very early in the transformation process. Be very
careful when touching other data structures and don't trust anything. Most
of the topology data hasn't been validated yet.
"""
def precheck_groups(topology: Box) -> None:
  auto_create_default = \
    topology.get('defaults.groups._auto_create',False) or \
    topology.get('groups._auto_create',False)     # auto-create could be set in defaults or on groups

  if 'groups' in topology:
    if check_group_data_sanity(topology):
      auto_create_members(topology,topology,auto_create_default)

  if 'groups' in topology.defaults:
    if check_group_data_sanity(topology,'defaults'):
      auto_create_members(topology.defaults,topology,False)

"""
init_groups:

* Check and adjust group data structures
* Check recursive groups
* Add nodes to groups based on node 'group' attribute

Please note that check_group_data_structure creates 'groups' element if needed
and 'adjust_groups' deletes it if there are no groups in the topology.
"""

def init_groups(topology: Box) -> None:
  if 'groups' in topology:
    check_group_data_structure(topology)

  if 'groups' in topology.defaults:
    check_group_data_structure(topology,'defaults',prune_members=True)
    for gname,gdata in topology.defaults.groups.items():
      if gname.find('_') == 0:
        continue

      if not gname in topology.groups:
        gdata._default_group = True

      topology.groups[gname] = gdata + topology.groups[gname]

  add_node_level_groups(topology)
  log.exit_on_error()

  check_recursive_groups(topology)
  log.exit_on_error()

def validate_groups(topology: Box) -> None:
  validate_group_data(topology)
  validate_group_data(topology,'defaults')
  log.exit_on_error()

def copy_group_data(topology: Box) -> None:
  copy_group_device_module(topology)
  copy_group_node_data(topology,'')                 # Copy all group data into nodes (potentially setting bgp.as)
  bgp.process_as_list(topology)
  create_bgp_autogroups(topology)                   # Create AS-based groups
  copy_group_node_data(topology,'as')               # And add group data from 'asxxxx' into nodes
  log.exit_on_error()
  if not topology.groups:
    del topology['groups']

'''
Copy custom config templates from groups into nodes
'''
def node_config_templates(topology: Box) -> None:
  if not 'groups' in topology:
    return

  '''
  Phase 1 - merge group config templates into nodes

  Traverse groups from more-specific to less specific, pushing config templates in front of
  the accumulated config list.

  End result: config templates sorted from less specific through more specific groups, ending
  with node templates.
  '''

  for group_name in reverse_topsort(topology):              # Iterate over all groups
    gdata = topology.groups[group_name]
    if not 'config' in gdata:                               # Skip a group if it has no 'config' attribute
      continue

    must_be_list(topology.groups[group_name],'config',f'groups.{group_name}')
    g_members = group_members(topology,group_name)          # Get node members of the group
    if not g_members and group_name != 'all':
      continue

    for name,ndata in topology.nodes.items():               # Iterate over nodes
      if name in g_members or group_name == 'all':          # Match members or 'all' group
        #
        # Make sure the node 'config' attribute is a list and prepend group config value to it
        # ... because the node config template might modify the settings from the group config template
        if not must_be_list(ndata,'config',f'nodes.{name}') is None:
          ndata.config = topology.groups[group_name].config + ndata.config

  '''
  Phase 2 - cleanup

  * Remove 'config' attributes from groups (just in case, they are no longer needed anyway)
  * Process node 'config' attributes to honor 'removal of prior templates' requests
  '''

  for group_name in topology.groups:
    if group_name.startswith('_'):                # Skip settings
      continue

    topology.groups[group_name].pop('config',None)

  for name,node in topology.nodes.items():
    if not 'config' in node:
      continue

    config_list: typing.List[str] = []
    for c in node.config:
      if c == '-':                 # Remove all prior templates
        config_list = []
      elif c[0] == '-':
        config_list = [ t for t in config_list if t != c [1:] ]
      else:
        config_list = config_list + [ c ]

    if config_list:
      node.config = config_list
    else:
      node.pop('config',None)

"""
Final step in group processing: remove settings from groups data structure,
so the templates don't have to guess whether they're dealing with groups
or settings
"""
def cleanup(topology: Box) -> None:
  if not 'groups' in topology:                    # No groups, no worries
    return

  for gname in list(topology.groups.keys()):      # Iterate over group names
    if gname.startswith('_'):                     # ... and if something starts with underscore, it's a setting
      topology.groups.pop(gname,None)             # ... so remove it

  if not topology.groups:                         # Anything left?
    topology.pop('groups',None)                   # ... nope, remove the whole 'groups' thingy
