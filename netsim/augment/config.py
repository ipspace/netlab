#
# Utility routines to augment configuration files
#

import typing
from box import Box

from .. import common

"""
Augment module attributes

* Copy data types from global to nodes (unless no_propagate is set)
* Copy data types from links to interfaces
* Copy data types from node to interfaces if an attribute is in the node_copy list
"""

def copy_datatypes(
      parent: typing.Optional[Box],                                   # Parent attributes (example: global)
      child: typing.Optional[Box],                                    # Child attributes (example: node)
      copy_list: list = [],                                           # Only copy these attributes (example: node_copy)
      skip_list: list = []) -> None:                                  # Skip these attributes (example: module.no_propagate)

  if not isinstance(child,Box) or not isinstance(parent,Box):         # Datatype propagation works only for box-to-box case
    return

  for k in child.keys():
    if copy_list and not k in copy_list:                              # If we have a copy list and the attribute is not in it, skip it
      continue

    if skip_list and k in skip_list:                                  # If we have a skip list and the attribute is in it, skip it
      continue

    if child[k] is None and k in parent:
      child[k] = parent[k]

def adjust_attributes(
      attr: Box,
      global_no_propagate: list = [],
      link_no_propagate: list = [],
      node_copy: list = []) -> None:

  copy_datatypes(                                                     # Copy global datatypes to node datatyps
    parent=attr.get('global',None),
    child=attr.get('node',None),
    skip_list=global_no_propagate)
  copy_datatypes(                                                     # Copy link datatypes to interface datatypes
    parent=attr.get('link',None),
    child=attr.get('interface',None),
    skip_list=link_no_propagate)
  if node_copy:                                                       # Copy node datatypes to interface datatypes
    copy_datatypes(                                                   # ... if the node_copy list is defined
      parent=attr.get('node',None),
      child=attr.get('interface',None),
      copy_list=node_copy)


def attributes(topology: Box) -> None:
  defaults=topology.defaults

  for modname,moddata in defaults.items():                            # Iterate over top-level defaults
    if not isinstance(moddata,Box) or not 'supported_on' in moddata:  # Skip everything that is not a module
      continue
    adjust_attributes(
      attr=moddata.attributes,
      global_no_propagate=moddata.get('no_propagate',[]),
      link_no_propagate=moddata.attributes.get('link_no_propagate',[]),
      node_copy=moddata.attributes.get('node_copy',[]))
