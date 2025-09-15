#
# Utility routines to augment configuration files
#

import textwrap
import typing

from box import Box, BoxList

from ..utils import files as _files
from ..utils import log

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
copy_merge_attributes: Copy or merge attribute definitions between various attribute namespaces

An attribute definition is copied/merged if:

* The attribute contains 'copy' keyword
* The attribute exists in the target namespace
'''
def copy_merge_attributes(attr: Box) -> None:
  for ns in attr.keys():                                              # Iterate over attribute namespaces
    if not isinstance(attr[ns],Box):                                  # This is clearly not an attribute namespace
      continue
    for attr_name in attr[ns].keys():                                 # Now iterate over attribute names
      if not isinstance(attr[ns][attr_name],Box):                     # Clearly not something that could request a copy
        continue
      source_ns = attr[ns][attr_name].get('copy',None) or attr[ns][attr_name].get('merge',None)
      if not source_ns:                                               # Do we have a copy/merge request?
        continue
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
      if 'copy' in attr[ns][attr_name]:                               # Request seems legit, now either...
        attr[ns][attr_name] = attr[source_ns][attr_name]              # ... copy the attribute
      elif 'merge' in attr[ns][attr_name]:                            # ... or merge the values
        attr[ns][attr_name] = attr[source_ns][attr_name] + attr[ns][attr_name]
        attr[ns][attr_name].pop('merge',None)                         # ... and remove the merge request

"""
copy_merge_device_features -- merge features across similar devices

The processing of merge requests is a bit awkward. For example, 'merge: ios' within csr.features.bgp means
'merge from ios.features.bgp'
"""
def copy_merge_device_features(
      data: Box,
      devices: typing.Optional[Box] = None,
      path: str = "") -> None:
  for kw in data.keys():
    if not isinstance(data[kw],Box):
      continue
    if 'merge' not in data[kw] and 'copy' not in data[kw]:
      copy_merge_device_features(data[kw],devices or data,f'{path}.{kw}' if path else kw)
    else:
      src_path = data[kw].get('merge',None) or data[kw].get('copy',None)
      if devices and path:
        if '.' in path:
          src_path += '.' + path.split('.',1)[1]
        src_path += '.' + kw
      else:
        devices = data

      if not src_path in devices:
        log.fatal(f'Cannot process copy/merge request in {path}.{kw}: {src_path} does not exist')

      data[kw] = (devices[src_path] + data[kw]) if 'merge' in data[kw] else devices[src_path]

'''
process_copy_requests: process 'copy attribute' requests from a late defaults data structure
'''
def process_copy_requests(defaults: Box) -> None:
  for def_name,def_data in defaults.items():                          # Iterate over default values
    if not isinstance(def_data,Box):                                  # Value not a dictionary => nothing to do
      continue
    if 'attributes' in def_data:
      copy_merge_attributes(def_data.attributes)                      # Process copy/merge attribute requests

  if 'devices' in defaults:
    copy_merge_device_features(defaults.devices)                      # Merge features across similar devices

def attributes(topology: Box) -> None:
  defaults=topology.defaults
  copy_merge_attributes(defaults.attributes)
  for modname,moddata in defaults.items():                            # Iterate over top-level defaults
    if not isinstance(moddata,Box) or not 'attributes' in moddata:    # Skip everything that does not have attributes
      continue
    copy_merge_attributes(moddata.attributes)
    adjust_attributes(
      attr=moddata.attributes,
      global_no_propagate=moddata.get('no_propagate',[]),
      link_no_propagate=moddata.attributes.get('link_no_propagate',[]),
      node_copy=moddata.attributes.get('node_copy',[]))

'''
paths: adjust system paths, replacing package: and topology: prefixes
'''
def paths(topology: Box) -> None:
  adjust_paths(topology.defaults.paths)
  make_paths_absolute(topology.defaults.paths)

'''
adjust_paths: prepend or append path elements to default paths
'''
def adjust_paths(paths: Box) -> None:
  if 'prepend' in paths and isinstance(paths.prepend,Box):
    adjust_path_list(paths.prepend,paths,False)
    paths.pop('prepend',None)

  if 'append' in paths and isinstance(paths.append,Box):
    adjust_path_list(paths.append,paths,True)
    paths.pop('append',None)

def adjust_path_list(adjust: Box, paths: Box, append: bool) -> None:
  for k,v in adjust.items():                                          # Iterate over prepend/append elements
    if isinstance(v,BoxList):                                         # ... act only on lists
      if k not in paths:                                              # Unknown path specification?
        paths[k] = v                                                  # ... just use it, maybe it's not a typo
      else:
        if isinstance(paths[k],BoxList):                              # Otherwise modify only if the target is a list
          paths[k] = paths[k] + v if append else v + paths[k]         # ... prepend or append the adjustment
    elif isinstance(v,Box) and isinstance(paths[k],Box):              # If both trees have further branches recurse
      adjust_path_list(adjust[k],paths[k],append)

'''
Recursive function that traverses the 'paths' tree and converts every list into
a list of absolute paths... unless the key starts with 'files' or 'tasks' in
which case the list is a list of potential file names and should not be changed.
'''
def make_paths_absolute(p_top: Box, parents: str = 'defaults.paths') -> None:
  for k in list(p_top.keys()):
    if k.startswith('files') or k.startswith('tasks'):
      p_top[k] = [ fn.replace('\n','') for fn in p_top[k] ]
      continue
    v = p_top[k]
    if isinstance(v,str):
      v = [ v ]
    if isinstance(v,BoxList):
      if log.debug_active('paths'):
        log.info(f'Paths: transforming/pruning {parents}.{k}',more_data=textwrap.indent(v.to_yaml(),'  '))
      p_top[k] = _files.absolute_search_path(v,skip_missing=True)
      if log.debug_active('paths'):
        log.info(f'Active path for {parents}.{k}',more_data=textwrap.indent(p_top[k].to_yaml(),'  '))
    elif isinstance(v,Box):
      make_paths_absolute(v,f'{parents}.{k}')
