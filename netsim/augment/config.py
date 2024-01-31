#
# Utility routines to augment configuration files
#

import typing
from box import Box
from ..utils import log,files as _files

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

'''
copy_attributes: Copy attribute definitions between various attribute namespaces

An attribute definition is copied/merged if:

* The attribute contains 'copy' keyword
* The attribute exists in the target namespace
'''
def copy_attributes(attr: Box) -> None:
  for ns in attr.keys():                                              # Iterate over attribute namespaces
    if not isinstance(attr[ns],Box):                                  # This is clearly not an attribute namespace
      continue
    for attr_name in attr[ns].keys():                                 # Now iterate over attribute names
      if not isinstance(attr[ns][attr_name],Box):                     # Clearly not something that could request a copy
        continue
      if 'copy' not in attr[ns][attr_name]:                           # Do we have a copy request?
        continue
      source_ns = attr[ns][attr_name]['copy']                         # Source namespace
      if not source_ns in attr:                                       # Unknown source namespace? Ignore the request
        log.error(
          'Incorrect source attribute namespace {source_ns} specified for {ns} attribute {attr_name}',
          log.IncorrectValue,'attributes')
        continue
      if not isinstance(attr[source_ns],Box):                         # Source NS not a box. Weird, skip it
        log.error(
          'Source attribute namespace {source_ns} specified for {ns} attribute {attr_name} is not a dictionary',
          log.IncorrectValue,'attributes')
        continue
      attr[ns][attr_name] = attr[source_ns][attr_name]                # Seems legit, copy attribute

'''
process_copy_requests: process 'copy attribute' requests from a late defaults data structure
'''
def process_copy_requests(defaults: Box) -> None:
  for def_name,def_data in defaults.items():                          # Iterate over default values
    if not isinstance(def_data,Box):                                  # Value not a dictionary => nothing to do
      continue
    if not 'attributes' in def_data:                                  # No attributes in this value => skip it
      continue
    copy_attributes(def_data.attributes)                              # Seems OK, process copy attribute requests

def attributes(topology: Box) -> None:
  defaults=topology.defaults

  for modname,moddata in defaults.items():                            # Iterate over top-level defaults
    if not isinstance(moddata,Box) or not 'attributes' in moddata:    # Skip everything that does not have attributes
      continue
    adjust_attributes(
      attr=moddata.attributes,
      global_no_propagate=moddata.get('no_propagate',[]),
      link_no_propagate=moddata.attributes.get('link_no_propagate',[]),
      node_copy=moddata.attributes.get('node_copy',[]))

'''
paths: adjust system paths, replacing package: and topology: prefixes
'''
def paths(topology: Box) -> None:
  make_paths_absolute(topology.defaults.paths)

'''
Recursive function that traverses the 'paths' tree and converts every list into
a list of absolute paths... unless the key starts with 'files' or 'tasks' in
which case the list is a list of potential file names and should not be changed.
'''
def make_paths_absolute(p_top: Box) -> None:
  for k in list(p_top.keys()):
    if k.startswith('files') or k.startswith('tasks'):
      p_top[k] = [ fn.replace('\n','') for fn in p_top[k] ]
      continue
    v = p_top[k]
    if isinstance(v,str):
      v = [ v ]
    if isinstance(v,list):
      p_top[k] = _files.absolute_search_path(v)
    elif isinstance(v,Box):
      make_paths_absolute(v)
