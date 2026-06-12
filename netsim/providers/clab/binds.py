#
# Containerlab provider module
#
import os

from box import Box

from ...data import append_to_list, filemaps
from ...utils import log
from .. import (
  READ_ONLY_SUFFIX,
  SHARED_PREFIX,
  SHARED_SUFFIX,
)

'''
normalize_clab_filemaps: convert clab templates and file binds into host:target lists
'''
def normalize_clab_filemaps(node: Box) -> None:
  for undot_key in ['clab.binds','clab.config_templates']:
    if not undot_key in node:
      continue
    filemaps.normalize_file_mapping(node,f'nodes.{node.name}',undot_key,'clab')

'''
add_config_filemaps: add device-level node/daemon_config dictionary to clab.config_templates dictionary
'''
def add_config_filemaps(node: Box, topology: Box) -> None:
  skip_config = node.get('skip_config',[])
  for kw in ('_daemon_config','_node_config'):
    if kw not in node:                            # Does the current node need non-ansible binds?
      continue

    # Adjust the configuration templates based on whether the skip_config is set
    #
    if skip_config:
      add_config = { k:v for k,v in node[kw].items() if k.replace('@','.') not in skip_config }
    else:
      add_config = node[kw]


    # Add the config templates in the correct priority: node config_templates
    # are preferred over _daemon_config which is preferred over _node_config
    # to allow Linux-based daemons to override Linux configuration (for example, routing)
    #
    node.clab.config_templates = add_config + node.clab.config_templates

'''
Add node files mapped through 'config_templates' to clab.binds
'''
def add_templates_to_binds(node: Box) -> None:
  if 'clab.config_templates' not in node:
    return
  
  bind_rev  = { item.target:item.source for item in node.get('clab.binds',[]) }
  for t_item in node.clab.config_templates:
    if not t_item.target:
      continue

    if t_item.target in bind_rev:
      log.error(
        f'Cannot map {t_item.source} into {t_item.target} on node {node.name}',
        more_data = [f'The output path is already mapped to {bind_rev[t_item.target]}'],
        category=log.IncorrectValue,
        module='clab')
      continue

    b_item = {'target': t_item.target}
    b_mode = t_item.get('mode','')
    if b_mode == SHARED_SUFFIX:
      b_item['source'] = f'node_files/{SHARED_PREFIX}{t_item.source}'
      b_item['mode'] = READ_ONLY_SUFFIX
    else:
      b_item['source'] = f'node_files/{node.name}/{t_item.source}'
      if b_mode == READ_ONLY_SUFFIX:
        b_item['mode'] = READ_ONLY_SUFFIX

    append_to_list(node.clab,'binds',b_item)

'''
check_node_binds: ensure all files mapped into a container exist
'''
def check_node_binds(node: Box) -> None:
  binds = node.get('clab.binds',[])
  if not binds:
    return

  for bind_item in binds:
    if os.path.exists(bind_item.source):
      continue
    log.error(
      f'File {bind_item.source} mapped to {bind_item.target} on node {node.name} does not exist',
      category=log.IncorrectValue,
      module='clab')
