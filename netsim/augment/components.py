'''
This module handles topology components

* Performs initial check of the components
* Expands included components into groups, nodes and links
'''


from box import Box

from .. import data
from ..data import global_vars
from ..data.types import must_be_dict, must_be_id, must_be_string
from ..utils import log
from . import links, nodes

'''
Validate topology components:

* Component name must be an identifier
* Component must be a dictionary
* nodes element must be a valid node specification
* links element must be a valid link list
'''
def validate_components(topology: Box) -> None:
  for cname in topology.components.keys():
    must_be_id(
      parent=None,
      key=cname,
      path=f'NOATTR:Component name {cname}',
      module='components')
    must_be_dict(
      parent=topology.components,
      key=cname,
      path='components',
      create_empty=True,
      module='components')
    cdata = topology.components[cname]

    if 'nodes' in cdata:
      cdata.nodes = nodes.create_node_dict(cdata.nodes)
    if 'links' in cdata:
      cdata.links = links.adjust_link_list(cdata.links,cdata.nodes,linkname_format=f'components.{cname}.links[{{link_cnt}}]')

'''
validate_include -- validate an include request

* Include value must be a string
* Include value must be a valid component name
'''

def validate_include(n_name: str, n_data: Box, topology: Box) -> bool:
  try:
    must_be_string(
      parent=n_data,
      key='include',
      path=f'nodes.{n_name}',
      module='components')
  except:
    return False

  if not n_data.include in topology.components:
    log.error(
      text=f'Component {n_data.include} used in node {n_name} not found',
      category=log.IncorrectValue,module='components')
    return False
  
  return True

'''
include_nodes -- include nodes from a component into the topology

Inputs:

* n_name: name of the node that includes the component
* c_data: component data
* topology: global lab topology

Iterate over all nodes in the component:

* Final node name is a combination of the include name and the component name
* If the node name already exists in the topology, report an error and skip it
* If the node is a nested include, validate it and recursively expand it.
  Otherwise, copy node data (to preserve the component) and add it to the topology

Also: check that the total number of nodes does not exceed the maximum allowed
'''
def include_nodes(n_name: str, c_data: Box, topology: Box) -> None:
  MAX_NODE_ID = global_vars.get_const('MAX_NODE_ID',150)

  for inc_name,inc_data in c_data.nodes.items():
    node_name = f'{n_name}_{inc_name}'
    must_be_id(
      parent=None,
      key=node_name,
      path=f'NOATTR:Node {inc_name} included in {n_name}',
      module='components')
    
    if node_name in topology.nodes:
      log.error(
        text=f'Node {inc_name} included in component {n_name} already exists in topology',
        category=log.IncorrectValue,module='components')
      continue

    if 'include' in inc_data:                               # Are we dealing with a nested include?
      if not validate_include(node_name,inc_data,topology): # Is the include request valid?
        continue                                            # ... no, move on
      expand_include(node_name,inc_data,topology)           # ... yes, do the include magic
    else:
      topology.nodes[node_name] = data.get_box(inc_data)    # Regular included node, just copy it
      topology.nodes[node_name].name = node_name            # Fix the name of the newly-generated node
      if len(topology.nodes) > MAX_NODE_ID:
        log.fatal(
          'Exceeded maximum node limit while adding node {node_name}',
          module='components',
          header=True)

def include_links(n_name: str, c_data: Box, topology: Box) -> None:
  for l_data in c_data.links:
    inc_link = data.get_box(l_data)                         # Create a copy of the link data structure
    inc_link._linkname = f'{n_name}_{inc_link._linkname}'   # ... fill in linkname
    inc_link.linkindex = links.get_next_linkindex(topology) # ... and link index
    inc_link.interfaces = list(inc_link.interfaces)         # Create a copy of the interface list
    for intf in inc_link.interfaces:                        # ... and adjust node names in interface list
      intf.node = f'{n_name}_{intf.node}'
    topology.links.append(inc_link)                         # Ready to add the new link to the global link list

def create_included_group(n_name: str, n_data: Box, c_data: Box, topology: Box) -> None:
  g_name = f'inc_{n_name}'
  if g_name in topology.groups:
    log.error(
      text=f'Group {g_name} already exists in topology',
      category=log.IncorrectValue,module='components')
    return

  g_data = topology.groups[g_name]
  g_data.members = []
  for m_name,m_data in c_data.nodes.items():
    if 'include' in m_data:
      g_data.members += [ f'inc_{n_name}_{m_name}' ]
    else:
      g_data.members += [ f'{n_name}_{m_name}' ]

  for k,v in c_data.items():
    if k in ['nodes','links']:
      continue
    topology.groups[g_name][k] = v

  for k,v in n_data.items():
    if not k in ['include','interfaces']:
      topology.groups[g_name][k] = v

def expand_include(n_name: str, n_data: Box, topology: Box) -> None:
  c_name = n_data.include
  c_data = topology.components[c_name]

  if 'nodes' in c_data:
    include_nodes(n_name,c_data,topology)
  if 'links' in c_data:
    include_links(n_name,c_data,topology)
  create_included_group(n_name,n_data,c_data,topology)

'''
We don't know the final node names When creating the link data structures,
so we can do a viability check, but cannot check the actual node names
for links involving nodes within components.

Once the components are expanded, the node names are final, and we can
do the final check.
'''
def validate_link_nodenames(topology: Box) -> None:
  for link in topology.get('links',[]):
    for intf in link.get('interfaces',[]):
      if intf.node not in topology.nodes:
        log.error(
          f'{link._linkname} refers to an unknown node {intf.node}',
          category=log.IncorrectValue,
          module='links')

'''
Expand included components into groups, nodes and links

* Validate components and exit on error
* For each included component (node with include attribute) expand it into
  groups, nodes and links
'''
def expand_components(topology: Box) -> None:
  if not 'components' in topology:
    return

  validate_components(topology)
  log.exit_on_error()

  for n_name in list(topology.nodes.keys()):                # Must use list() to avoid dictionary changed error
    n_data = topology.nodes[n_name]                         # Get a pointer to node data
    if not 'include' in n_data:                             # Not an included component, move on
      continue

    topology.nodes.pop(n_name,None)                         # ... and immediately remove include request from nodes
    if not validate_include(n_name,n_data,topology):        # Is the include request valid?
      continue                                              # ... no, move on, will abort before exit
    expand_include(n_name,n_data,topology)                  # ... yes, do the include magic

  validate_link_nodenames(topology)                         # After expanding components, revalidate node names on links
  log.exit_on_error()
  topology.pop('components',None)

#  print(topology.groups.to_yaml())