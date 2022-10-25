'''
Add group support. This module handles group-related data structures and
data transformation. The end result is a dictionary of groups in 'groups'
top-level element. That dictionary is merged from global- and node-level parameters
'''

import typing

from box import Box

from .. import common
from .. import data
from ..data.validate import must_be_dict,must_be_list,must_be_string,validate_attributes
from . import nodes

'''
Return members of the specified group. Recurse through child groups if needed
'''
def group_members(topology: Box, group: str, count: int = 0) -> list:
  members: typing.List[str] = []
  if not group in topology.groups:  # pragma: no cover (just-in case catch, impossible to get here)
    common.error(
      f'Internal error: unknown group {group}',
      common.IncorrectValue,
      'groups')                    
    return []                      

  if count > 99:                    # pragma: no cover (impossible to get here, recursive groups are checked elsewhere)
    common.fatal(
      'Recursive group definition, aborting',
      'groups')                    

  for m in topology.groups[group].members:
    if m in topology.nodes:
      members = members + [ m ]
    if m in topology.groups:
      members = members + group_members(topology,m,count + 1)

  return members

'''
Check validity of 'groups' data structure
'''
def check_group_data_structure(topology: Box) -> None:
  if not 'groups' in topology:
    topology.groups = Box({},default_box=True,box_dots=True)

  if must_be_dict(topology,'groups','topology',create_empty=True,module='groups') is None:
    return

  '''
  Transform group-as-list into group-as-dictionary
  '''
  for grp in topology.groups.keys():
    if isinstance(topology.groups[grp],list):
      topology.groups[grp] = { 'members': topology.groups[grp] }
    if grp in topology.nodes:
      common.error(
        f"group {grp} is also a node name. I can't deal with that level of confusion",
        common.IncorrectValue,
        'groups')

  '''
  Sanity checks on global group data
  '''

  list_of_modules = [ m for m in topology.defaults.keys() \
                          if isinstance(topology.defaults[m],dict) \
                            and 'supported_on' in topology.defaults[m] ]
  group_attr = topology.defaults.attributes.group

  for grp,gdata in topology.groups.items():
    if must_be_dict(topology.groups,grp,'topology.groups',create_empty=True,module='groups') is None:
      continue

    gpath=f'topology.groups.{grp}'
    g_modules = gdata.get('module',[])
    if g_modules:                                                     # Modules specified in the group -- we know what these nodes will use
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
      module_source=gm_source)

    if not 'members' in gdata:
      gdata.members = []

    if grp == 'all' and gdata.members:
      common.error('Group "all" should not have explicit members')

    must_be_dict(gdata,'vars',gpath,create_empty=False,module='groups')
    must_be_dict(gdata,'node_data',gpath,create_empty=False,module='groups')
    must_be_list(gdata,'config',gpath,create_empty=False,module='groups')
    must_be_list(gdata,'module',gpath,create_empty=False,module='groups',valid_values=list_of_modules)
    must_be_string(gdata,'device',gpath,module='groups',valid_values=list(topology.defaults.devices))

    if 'node_data' in gdata:                          # Validate node_data attributes (if any)
      validate_attributes(
        data=gdata.node_data,
        topology=topology,
        data_path=f'{gpath}.node_data',
        data_name='node',
        attr_list=[ 'node' ],
        module='groups',
        modules=g_modules,
        module_source=gm_source)

    for k in list(gdata.keys()):                      # Then move (validated) group node attributes into node_data
      if k in group_attr:
        continue
      gdata.node_data[k] = gdata[k]
      gdata.pop(k,None)

    if must_be_list(gdata,'members',gpath,create_empty=False,module='groups') is None:
      continue

    for n in gdata.members:
      if not n in topology.nodes and not n in topology.groups:
        common.error('Member %s of group %s is not a valid node or group name' % (n,grp))


'''
Add node-level group settings to global groups
'''
def add_node_level_groups(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if not 'group' in n:
      continue

    if isinstance(n.group,str):                           # Node group should be a list
      n.group = [ n.group ]                               # Convert a string value into a single-element list

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
    common.fatal(
      'Internal error: unknown group in check_recursive_chain') 
    return None  

  chain = chain + [ group ]
  for m in topology.groups[group].members:
    if m in chain:
      chain = chain + [ m ]
      common.error(f'Recursive group definition chain {chain}', common.IncorrectValue, 'groups')
      return chain
    if m in topology.groups:
      if check_recursive_chain(topology,chain,m):
        return chain

  return None

def check_recursive_groups(topology : Box) -> None:
  for gname in topology.groups.keys():
    if check_recursive_chain(topology,[],gname):
      return

def reverse_topsort(topology: Box) -> list:
  group_copy = Box(topology.groups)            # Make a copy of the group dictionary
  sort_list: typing.List[str] = []
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
    if 'device' in gdata or 'module' in gdata:
      g_members = group_members(topology,grp)
      if g_members:
        for name,ndata in topology.nodes.items():
          if name in g_members:
            for attr in ('device','module'):
              if attr in gdata and not attr in ndata:
                ndata[attr] = gdata[attr]
      else:
        common.error(
          f'Cannot use "module" or "device" attribute on in group {grp} that has no direct or indirect members',
          common.IncorrectValue,
          'groups')

'''
Utility function: merge group value into node value. Deals with scalars and dicts
'''
def merge_node_data(ndata: Box, k: str, v: typing.Any, node_name: str, group_name: str) -> None:
  if not k in ndata:
    ndata[k] = v
  if isinstance(ndata[k],dict):
    if isinstance(v,dict):
      ndata[k] = ndata[k] + v
    else:
      common.error(
        f'Cannot merge non-dictionary node_data {k} from group {group_name} into node {node_name}',
        common.IncorrectValue,
        'groups')

'''
Copy node data from group into group members
'''
def copy_group_node_data(topology: Box) -> None:
  for grp in reverse_topsort(topology):
    gdata = topology.groups[grp]
    if 'node_data' in gdata:
      node_data_keys  = set(gdata.node_data.keys())                   # You cannot set device type or node modules with
      node_data_wrong = False                                         # ... node data, those attributes have to be set
      for k in ('module','device'):                                   # ... at group level
        if k in node_data_keys:
          common.error(
            f'Cannot use attribute {k} in node_data in group {grp}, set it as a group attribute',
            common.IncorrectValue,
            'groups')
          node_data_wrong = True
      if node_data_wrong:
        continue

      g_members = group_members(topology,grp)
      for name,ndata in topology.nodes.items():
        if name in g_members:
          for k,v in gdata.node_data.items():   # Have to go one level deeper, changing ndata value wouldn't work
            merge_node_data(ndata,k,v,ndata.name,grp)

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
    #
    # Find groups with node_data dictionaries
    if must_be_dict(gdata,f'node_data.{key}',f'groups.{gname}',module=module,create_empty=False):
      for obj_name in list(gdata.node_data[key].keys()):
        if gdata.node_data[key][obj_name] is None:
          gdata.node_data[key][obj_name] = {}
        obj_data =  gdata.node_data[key][obj_name]
        if not obj_name in topology[key] or topology[key][obj_name] is None:
          topology[key][obj_name] = {}
        for attr in unique_keys:
          if attr in topology[key][obj_name] and attr in obj_data and \
             topology[key][obj_name][attr] != obj_data[attr]:                          # Unique key present on both ends and not equal
            common.error(
              f'Cannot redefine {key} attribute {attr} for {key}.{obj_name} from node_data in group {gname}',
              common.IncorrectValue,
              module)
        for attr in copy_keys:
          if attr in obj_data and attr not in topology[key][obj_name]:
            topology[key][obj_name][attr] = obj_data[attr]

#
# init_groups:
#
# * Check and adjust group data structures
# * Check recursive groups
# * Add nodes to groups based on node 'group' attribute
#
# Please note that check_group_data_structure creates 'groups' element if needed
# and 'adjust_groups' deletes it if there are no groups in the topology.
#
def init_groups(topology: Box) -> None:
  check_group_data_structure(topology)
  add_node_level_groups(topology)
  common.exit_on_error()

  check_recursive_groups(topology)
  common.exit_on_error()

  copy_group_device_module(topology)

#
# adjust_groups:
#
# * Copy group data into nodes
#
# We have to split the group initialization code into two phases
# due to BGP auto groups.
#
def adjust_groups(topology: Box) -> None:
  copy_group_node_data(topology)
  common.exit_on_error()

  '''
  Finally, remove 'groups' topology element if it's not needed
  '''
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
