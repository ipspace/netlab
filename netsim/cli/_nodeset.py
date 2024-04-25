'''
This module implements nodesets -- a subnet of nodes specified in the
'--node' parameter of some netlab commands.

The nodeset string specification could contain a single element or
multiple elements separated by commas. Each element could be a 
node name or a glob.
'''

import fnmatch
from box import Box
from ..utils import log
from .. import data

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
"""
def parse_nodeset(ns: str, topology: Box) -> list:
  n_names = list(topology.nodes.keys())
  n_list: list = []
  for n_element in ns.split(','):
    if is_glob(n_element):
      if not add_glob(n_element,n_names,n_list):
        log.error(f'Wildcard node specification {n_element} does not match any nodes',log.IncorrectValue,'')
    else:
      if n_element not in n_names:
        log.error(f'Invalid node name {n_element}',log.IncorrectValue,'')
      else:
        if n_element not in n_list:
          n_list.append(n_element)

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
