import typing
from box import Box
from netsim import api,data
from netsim.utils import log,strings
from netsim.augment.links import adjust_link_list

_config_name = 'fabric'


'''
create_node -- create a node in the fabric
'''

def create_node(n_template: str, n_id: int) -> Box:
  name = strings.eval_format(n_template,{ 'count': n_id })  # Get node name give name template and fabric count
  node = data.get_box({'name': name})                       # Create a new box with .name key
  node.interfaces = []                                      # Interfaces must be an empty list (we're past node normalization)
  node._fabric_count = n_id                                 # ... and we have to remember the fabric counter
  return node

'''
add_group -- add a fabric group
'''

def add_group(groups: Box, g_name: str, g_list: list) -> None:
  groups[g_name].members = [ n.name for n in g_list ]       # Create a new group with 'members' attribute

'''
extract_params -- extract formatted or non-formatted parameters

The function recursively iterates over dictionaries, removing either formatted strings
(if fmt is False) or everything but formatted strings (if fmt is True).

When searching for formatted strings, the function also removes empty dictionaries,
ending with the minimum tree containg formatted strings. The same pruning is not needed
for non-formatted (group) parameters as they may contain empty dictionaries (example: VLANs)
'''

def extract_params(params: Box, fmt: bool) -> Box:
  for k in list(params.keys()):                   # Iterate over all keys in the dictionary
    if isinstance(params[k],Box):                 # Child dictionary?
      extract_params(params[k],fmt)               # ... do the same thing recursively
      if not params[k] and fmt:                   # ... and prune if we're collecting formatted parameters
        params.pop(k,None)
    elif isinstance(params[k],str):               # String value?
      if ('{' in params[k]) != fmt:               # ... does it match the expected formatting state?
        params.pop(k,None)                        # ... nope, prune
    elif fmt:
      params.pop(k,None)                          # When pruning formatted tree, drop all other values

  return params                                   # ... and return cleaned-up data structure

'''
format_node_params -- add parameters to nodes

The function recursively walks the dictionary tree and formats all string
instances, trying to convert them to ints (because the formatted expression
might turn out to be an int)
'''
def format_node_params(params: Box, node: Box) -> Box:
  for k in params.keys():                         # Walk over dictionary keys
    if isinstance(params[k],Box):                 # ... recurse into child dictionaries
      format_node_params(params[k],node)
    elif isinstance(params[k],str):               # Oh, found a string
      #
      # Build formatting parameters from node values and _fabric_count renamed to 'count'
      # This also creates a new copy of the dictionary
      #
      node_params = node + { 'count' : node._fabric_count }
      value = strings.eval_format(params[k],node_params)
      try:
        params[k] = int(value)                    # Try to convert value into int
      except:
        params[k] = value                         # ... if int conversion failed, store the string value

  return params                                   # ... and return the fully-evaluated tree

'''
adjust_group_parameters -- copy leaf/spine attributes to nodes or groups
'''

def adjust_group_parameters(
      group_name: str,                            # Name of the group
      groups: Box,                                # Groups dictionary
      node_list: list,                            # List of nodes in this fabric layer
      params: Box) -> None:                       # Fabric layer parameters

  params = params + {}                            # First create a local copy of the parameters
  for k in ('name','group'):                      # ... and pop fabric-specific attributes
    params.pop(k,None)

  if not params:
    return

  node_params = extract_params(params + {},fmt=True)        # Parameters with formatting strings will be copied to nodes
  group_params = extract_params(params + {},fmt=False)      # ... all other parameters will be copied to groups

  if group_params:                                          # Do we have any group parameters?
    groups[group_name] = groups[group_name] + group_params  # ... no problem, just add them to our group

  if node_params:                                           # Dealing with node parameters is more complex
    for idx,node in enumerate(node_list):                   # ... iterate over node list
      #
      # For every node, format a fresh copy of node parameters and add that to the node Box
      # Store the modified box in the node_list (easier than doing key-by-key merge)
      #
      node_list[idx] = node + format_node_params(node_params + {},node)

'''
generate_fabric -- given number of leafs and spines, generate fabric nodes, links and groups
'''

def generate_fabric(topology: Box, l_cnt: int, s_cnt: int) -> typing.Tuple[Box, Box, typing.List[Box]]:
  #
  # Get the fabric settings: leaf node names, spine node names...
  defaults = topology.defaults
  l_name = topology.get('fabric.leaf.name',defaults.fabric.leaf.name or 'L{count}')
  s_name = topology.get('fabric.spine.name',defaults.fabric.spine.name or 'S{count}')

  node_lists = data.get_box({ 'leaf': [], 'spine': [] })    # Create empty list of leafs and spines

  for count in range(1,l_cnt+1):
    node_lists.leaf.append(create_node(l_name,count))       # Create leaf nodes, append them to leaf list

  for count in range(1,s_cnt+1):
    node_lists.spine.append(create_node(s_name,count))      # Create spine nodes, append them to spine list

  links = []
  for l in node_lists.leaf:                                 # Links are a cartesian product of leafs
    for s in node_lists.spine:                              # ... and spines
      link = data.get_empty_box()                           # Every link starts as an empty box
      link[l.name] = {}                                     # ... attach leaf node to it
      link[s.name] = {}                                     # ... and the spine node
      links.append(link)                                    # Append the link to fabric link list

  groups = data.get_empty_box()                             # Next step: create fabric groups
  for role in ('leaf','spine'):
    #
    # Get the fabric group name, create the new group
    group_name = topology.get(f'fabric.{role}.group',defaults.fabric[role].group or f'{role}s')
    add_group(groups,group_name,node_lists[role])

    adjust_group_parameters(                                # Adjust group/node parameters
      group_name,
      groups,
      node_lists[role],
      topology.get(f'fabric.{role}',{}))

  nodes = data.get_empty_box()                              # Finally create nodes
  for n in node_lists.leaf + node_lists.spine:              # ... copying leaf + spine lists
    nodes[n.name] = n                                       # ... into the nodes dictionary structure

  # Almost there. Now that we have the definitive nodes dictionary, we can transform
  # links into the final data structure
  #
  links = adjust_link_list(links,nodes,'fabric[{link_cnt}]')

  return(groups,nodes,links)                                # And return everything we created

'''
debug_fabric -- print auto-generated fabric data
'''
def debug_fabric(topology: Box, groups: Box, nodes: Box, links: list) -> None:
  print('Fabric parameters')
  print('=' * 80)
  print(strings.get_yaml_string(topology.fabric))

  print('Fabric groups')
  print('=' * 80)
  print(strings.get_yaml_string(groups))

  print('Fabric nodes')
  print('=' * 80)
  print(strings.get_yaml_string(nodes))

  print('Fabric links')
  print('=' * 80)
  print(strings.get_yaml_string(links))

'''
The fabric is generated during plugin initialization phase
'''

def topology_expand(topology: Box) -> None:
  if not 'fabric' in topology:
    return

  l_cnt = topology.get('fabric.leafs',1)                    # Get number of leafs and spines
  s_cnt = topology.get('fabric.spines',1)                   # Missing values ==> 1, validation code will complain in a minute ;)

  # Create the fabric groups, nodes and links
  (grp,nodes,links) = generate_fabric(topology,l_cnt,s_cnt)

  if topology.get('fabric.debug',None):                     # Dump the fabric data for debugging purposes
    debug_fabric(topology,grp,nodes,links)

  # And now for the fun part: merging fabric data with topology data
  # 
  # Groups are special. We can add fabric groups to topology groups, but that won't
  # merge the 'members' lists.
  topology.groups = grp + topology.groups
  for g in grp.keys():                                            # Iterate over all groups
    all_members = topology.groups[g].members + grp[g].members     # ... combine the member lists
    topology.groups[g].members = sorted(list(set(all_members)))   # ... and use a sorted set to make the list unique and deterministic

  topology.nodes = nodes + topology.nodes                         # Nodes are trivial -- add fabric nodes to topology nodes
  topology.links = links + topology.get('links',[])               # ... and prepend fabric links to topology links
