'''
Add group support. This module handles group-related data structures and
data transformation. The end result is a dictionary of groups in 'groups'
top-level element. That dictionary is merged from global- and node-level parameters
'''

import typing
import re

from box import Box

from ..utils import log
from .. import data
from .. import modules
from ..modules import bgp
from ..data import get_box,get_empty_box
from ..data.validate import validate_attributes,get_object_attributes
from ..data.types import must_be_dict,must_be_list,must_be_id,transform_asdot
from . import nodes

'''
Return members of the specified group. Recurse through child groups if needed
'''
def group_members(topology: Box, group: str, count: int = 0) -> list:
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

  for m in topology.groups[group].members:
    if m in topology.nodes:
      members = members + [ m ]
    if m in topology.groups:
      members = members + group_members(topology,m,count + 1)

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

  if must_be_dict(parent,'groups',parent_path,create_empty=True,module='groups') is None:
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

def check_group_data_structure(
      topology: Box,
      parent_path: typing.Optional[str] = '',
      prune_members: typing.Optional[bool] = False) -> None:

  parent = topology.get(parent_path) if parent_path else topology
  grp_namespace = f'{parent_path} ' if parent_path else ''

  '''
  Sanity checks on global group data
  '''

  list_of_modules = modules.list_of_modules(topology)
  group_attr = topology.defaults.attributes.group

  # Allow provider- and tool- specific node attributes
  extra = get_object_attributes(['providers','tools'],topology)

  for grp,gdata in parent.groups.items():
    if grp.startswith('_'):                       # Skip stuff starting with underscore
      continue                                    # ... could be system settings

    must_be_id(parent=None,key=grp,path=f'NOATTR:group name {grp}',module='groups')

    gpath = f'{parent_path or "topology"}.groups'
    if must_be_dict(parent.groups,grp,gpath,create_empty=True,module='groups') is None:
      continue

    gpath=f'{gpath}.{grp}'
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
      data_name='group',
      attr_list=[ 'group','node' ],
      module='groups',
      modules=g_modules,
      module_source=gm_source,
      ignored=['_','netlab_','ansible_'],   # Ignore attributes starting with _, netlab_ or ansible_
      extra_attributes=extra)               # Allow provider- and tool-specific settings (not checked at the moment)

    if not 'members' in gdata:
      gdata.members = []

    if grp == 'all' and gdata.members:
      log.error(
        text=f'{grp_namespace}group "all" should not have explicit members',
        category=log.IncorrectValue,
        module='groups')

    must_be_list(gdata,'module',gpath,create_empty=False,module='groups',valid_values=sorted(list_of_modules))

    if 'node_data' in gdata:                 # Validate node_data attributes (if any)
      log.error(
        text=f'Group {grp} uses an obsolete attribute node_data. Migrate node parameters into group definition',
        category=Warning,
        module='groups')

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

    if must_be_list(gdata,'members',gpath,create_empty=False,module='groups') is None:
      continue

    if prune_members:
      gdata.members = [ n for n in gdata.members if n in topology.nodes or n in parent.groups ]
    else:
      for n in gdata.members:
        if not n in topology.nodes and not n in parent.groups:
          log.error(
            text=f'Member {n} of {grp_namespace}group {grp} is not a valid node or group name',
            category=log.IncorrectValue,
            module='groups')

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

  parent_path = 'groups' if parent is topology else 'defaults.groups'
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

      if n in topology.nodes:                     # Skip if the member is already a known node
        continue

      topology.nodes[n].name = n                  # Otherwise create an empty node data structure
      topology.nodes[n].interfaces = []           # ... with an empty interface list
  
  '''
  Transform group-as-list into group-as-dictionary
  '''
  for grp in parent.groups.keys():
    gpath = f'{parent_path or "topology"}.groups.{grp}'

'''
Add node-level group settings to global groups
'''
def add_node_level_groups(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if not 'group' in n:
      continue

    must_be_list(n,'group',f'nodes.{name}')

    for grpname in n.group:
      if not grpname in topology.groups:
        topology.groups[grpname] = { 'members': [] }      # Create an empty new group if needed

      if not name in topology.groups[grpname].members:  # Node not yet in the target group
        topology.groups[grpname].members.append(name)   # Add node to the end of the member list

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
  for grp in reverse_topsort(topology):
    gdata = topology.groups[grp]
    if not 'device' in gdata and not 'module' in gdata:
      continue                                                        # This group is not interesting, move on

    if log.debug_active('groups'):
      print(f'Setting device/module for group {grp}')
    g_members = group_members(topology,grp)
    if not g_members and not gdata.get('_default_group',False):
      log.error(
        f'Cannot use "module" or "device" attribute on in group {grp} that has no direct or indirect members',
        log.IncorrectValue,
        'groups')
      continue

    for name in g_members:                                            # Iterate over group members
      if not name in topology.nodes:                                  # Member not a node? Move on...
        continue

      ndata = topology.nodes[name]
      if 'device' in gdata and not 'device' in ndata:                 # Copy device from group data to node data
        ndata.device = gdata.device
        if log.debug_active('groups'):
          print(f'... setting {name}.device to {gdata.device}')

      if 'module' in gdata:                                           # Merge group modules with device modules
        ndata.module = ndata.module or []                             # Make sure node.module is a list
        for m in gdata.module:                                        # Now iterate over group modules
          if not m in ndata.module:                                   # ... and add missing modules to nodes
            ndata.module.append(m)

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

    g_members = group_members(topology,grp)                           # Get recursive list of members
    if log.debug_active('groups'):
      print(f'copy node data {grp}: {gdata.node_data}')
    for name in g_members:                                            # Iterate over group members
      if not name in topology.nodes:                                  # Member is not a node, skip it
        continue

      if log.debug_active('groups'):
        print(f'... merging node data with {name}')
      merge_data = data.get_box(gdata.node_data)
      if 'module' in topology.nodes[name]:
        for m in topo_modules:
          if not m in topology.nodes[name].module:
            merge_data.pop(m,None)

      topology.nodes[name] = merge_data + topology.nodes[name]

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

  for gname,gdata in topology.groups.items():                   # Sanity check: BGP autogroups should not have static members
    if re.match('as\\d+$',gname):
      if gdata.get('members',None):                             # Well, it's OK to have an empty list of members ;)
        log.error(
          f'BGP AS group {gname} should not have static members',
          log.IncorrectValue,
          'groups')

  for n_name,n_data in topology.nodes.items():                  # Now iterate over nodes
    n_module = n_data.get('module',g_module)                    # Get node or global module (global modules haven't been propagated yet)
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
    if not 'members' in topology.groups[grpname]:               # Set members of a new group to an empty list
      topology.groups[grpname].members = []                     # ... because we're using Box this also creates an empty group dict

    topology.groups[grpname].members.append(n_name)             # ... and append the node to AS group

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

  for group_name in reverse_topsort(topology):
    if not 'config' in topology.groups[group_name]:
      continue

    must_be_list(topology.groups[group_name],'config',f'groups.{group_name}')
    g_members = group_members(topology,group_name)
    for name,ndata in topology.nodes.items():
      if name in g_members or group_name == 'all':
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
