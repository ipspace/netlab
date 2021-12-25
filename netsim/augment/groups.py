'''
Add group support. This module handles group-related data structures and
data transformation. The end result is a dictionary of groups in 'groups'
top-level element. That dictionary is merged from global- and node-level parameters
'''

import typing

from box import Box

from .. import common
from . import nodes

group_attr = [ 'members','vars','config','node_data' ]

'''
Return members of the specified group. Recurse through child groups if needed
'''
def group_members(topology: Box, group: str, count: int = 0) -> list:
  members: typing.List[str] = []
  if not group in topology.groups:
    common.error(f'Internal error: unknown group {group}',common.IncorrectValue,'groups')
    return []

  if count > 99:
    common.fatal('Recursive group definition, aborting','groups')

  for m in topology.groups[group].members:
    if m in topology.nodes_map:
      members = members + [ m ]
    if m in topology.groups:
      members = members + group_members(topology,m,count + 1)

  return members

'''
Check validity of 'groups' data structure
'''
def check_group_data_structure(topology: Box) -> None:
  nodes.rebuild_nodes_map(topology)

  if not 'groups' in topology:
    topology.groups = Box({},default_box=True,box_dots=True)

  if not isinstance(topology.groups,dict):
    common.error('Groups topology-level element should be a dictionary of groups')
    return

  '''
  Transform group-as-list into group-as-dictionary
  '''
  for grp in topology.groups.keys():
    if isinstance(topology.groups[grp],list):
      topology.groups[grp] = { 'members': topology.groups[grp] }
    if grp in topology.nodes_map:
      common.error(
        f"group {grp} is also a node name. I can't deal with that level of confusion",
        common.IncorrectValue,
        'groups')

  '''
  Sanity checks on global group data
  '''
  for grp,gdata in topology.groups.items():
    if not isinstance(gdata,Box):
      common.error('Group definition should be a dictionary: %s' % grp)
      continue

    if not 'members' in gdata:
      gdata.members = []

    if grp == 'all' and gdata.members:
      common.error('Group "all" should not have explicit members')

    if 'vars' in gdata:
      if not isinstance(gdata.vars,dict):
        common.error('Group variables must be a dictionary: %s' % grp)

    if 'config' in gdata:
      if not isinstance(gdata.config,list):
        if not isinstance(gdata.config,str):
          common.error('Config group attribute should be a string or a list: %s' % grp)
        else:
          gdata.config = [ gdata.config ]

    for k in gdata.keys():
      if not k in group_attr:
        common.error('Unknown attribute "%s" in group %s' % (k,grp))

    if not isinstance(gdata.members,list):
      common.error('Group members must be a list of nodes or groups: %s' % grp)
      continue

    for n in gdata.members:
      if not n in topology.nodes_map and not n in topology.groups:
        common.error('Member %s of group %s is not a valid node or group name' % (n,grp))


'''
Add node-level group settings to global groups
'''
def add_node_level_groups(topology: Box) -> None:
  for n in topology.nodes:
    if not 'group' in n:
      continue

    if isinstance(n.group,str):                           # Node group should be a list
      n.group = [ n.group ]                               # Convert a string value into a single-element list

    for grpname in n.group:
      if not grpname in topology.groups:
        topology.groups[grpname] = { 'members': [] }      # Create an empty new group if needed

      if not n.name in topology.groups[grpname].members:  # Node not yet in the target group
        topology.groups[grpname].members.append(n.name)   # Add node to the end of the member list

'''
Check recursive group definitions
'''

def check_recursive_chain(topology: Box, chain: list, group: str) -> typing.Optional[list]:
  if not group in topology.groups:
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
Copy node data from group into group members
'''
def copy_group_node_data(topology: Box) -> None:
  for grp in reverse_topsort(topology):
    gdata = topology.groups[grp]
    g_members = group_members(topology,grp)
    if 'node_data' in gdata:
      for ndata in topology.nodes:              # Have to iterate over original node data (nodes_map contains a copy)
        if ndata.name in g_members:
          for k,v in gdata.node_data.items():   # Have to go one level deeper, changing ndata value wouldn't work
            if not k in ndata:
              ndata[k] = v
            if isinstance(ndata[k],dict):
              if isinstance(v,dict):
                ndata[k] = ndata[k] + v
              else:
                common.error(
                  f'Cannot merge non-dictionary node_data {k} from group {grp} into node {ndata.name}',
                  common.IncorrectValue,
                  'groups')

def adjust_groups(topology: Box) -> None:
  check_group_data_structure(topology)
  add_node_level_groups(topology)
  common.exit_on_error()

  if not 'groups' in topology:
    return

  check_recursive_groups(topology)
  common.exit_on_error()

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

    common.must_be_list(topology.groups[group_name],'config',f'groups.{group_name}')
    g_members = group_members(topology,group_name)
    for ndata in topology.nodes:
      if ndata.name in g_members or group_name == 'all':
        common.must_be_list(ndata,'config',f'nodes.{ndata.name}')
        ndata.config = topology.groups[group_name].config + ndata.config


  '''
  Phase 2 - cleanup

  * Remove 'config' attributes from groups (just in case, they are no longer needed anyway)
  * Process node 'config' attributes to honor 'removal of prior templates' requests
  '''

  for group_name in topology.groups:
    topology.groups[group_name].pop('config',None)

  for node in topology.nodes:
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
