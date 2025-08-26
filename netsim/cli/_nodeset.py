'''
This module implements nodesets -- a subnet of nodes specified in the
'--node' parameter of some netlab commands.

The nodeset string specification could contain a single element or
multiple elements separated by commas. Each element could be a 
node name or a glob.
'''

import fnmatch

from box import Box

from .. import data
from ..augment import groups
from ..utils import log


# Is a string a glob expression?
#
def is_glob(pattern: str) -> bool:
  return any([c in pattern for c in ['*','?','[']])

# Find all names matching a glob expression and append them to the node name list
#
def add_glob(glob: str, names: list, results: list) -> int:
  g_count = 0
  for name in names:
    if fnmatch.fnmatch(name,glob):
      g_count += 1
      if name not in results:
        results.append(name)

  return g_count

"""
Given a nodeset (as a string) and the lab topology, return the list
of nodes matching the nodeset. Generate errors as appropriate and
abort if needed.

Nodeset is a comma-separate list of:

* Node names
* Group names
* Glob expressions matching node names

The function does its best to maintain the order in which the nodes
were specified.
"""
def parse_nodeset(ns: str, topology: Box) -> list:
  n_names = list(topology.nodes.keys())
  d_names = list(topology.defaults.devices.keys())
  n_list: list = []
  for n_element in ns.split(','):
    if n_element in n_list:
      continue

    if is_glob(n_element):
      if not add_glob(n_element,n_names,n_list):
        log.error(f'Wildcard node specification {n_element} does not match any nodes',module='-',skip_header=True)
    elif n_element in topology.groups:
      node_list = groups.group_members(topology,n_element)
      n_list = n_list + [ n for n in node_list if n not in n_list ]
    elif n_element in n_names:
      n_list.append(n_element)
    elif n_element.lower() == 'all':
      add_glob('*',n_names,n_list)
    elif n_element in d_names:
      d_list = [ n_name for n_name,n_data in topology.nodes.items() if n_data.device == n_element ]
      if d_list:
        n_list = n_list + [ n_name for n_name in d_list if n_name not in n_list ]
      else:
        log.error(f'The current lab topology has no {n_element} devices',module='-',skip_header=True)
    else:
      log.error(f'{n_element} is not a glob or a valid node, group, or device name',module='-',skip_header=True)

  log.exit_on_error()
  return n_list

"""
Given a lab topology and a list of nodes, create a subset of the topology (to make our life easier)
"""
def get_nodeset(topology: Box, node_list: list) -> Box:
  pruned_box = data.get_box(topology)
  for node in list(pruned_box.nodes.keys()):
    if node not in node_list:
      pruned_box.nodes.pop(node,None)

  return pruned_box
