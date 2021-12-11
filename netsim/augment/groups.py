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

def adjust_groups(topology: Box) -> None:
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
      common.error('Group members must be a list of nodes: %s' % grp)
      continue

    for n in gdata.members:
      if not n in topology.nodes_map:
        common.error('Member %s of group %s is not a valid node name' % (n,grp))

  '''
  Add node-level group settings to global groups
  '''
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
  Copy node data from group into group members
  '''
  for grp,gdata in topology.groups.items():
    if 'node_data' in gdata:
      for ndata in topology.nodes:              # Have to iterate over original node data (nodes_map contains a copy)
        if ndata.name in gdata.members:
          for k,v in gdata.node_data.items():   # Have to go one level deeper, changing ndata value wouldn't work
            ndata[k] = ndata.get(k,{}) + v

  '''
  Finally, remove 'groups' topology element if it's not needed
  '''
  if not topology.groups:
    del topology['groups']
