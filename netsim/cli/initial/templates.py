"""
The template-handling utility functions shared across 'netlab initial' modules
"""

import os
import typing

from box import Box

from ...augment import devices
from ...outputs.ansible import get_host_addresses
from ...outputs.common import adjust_inventory_host
from ...utils import files as _files
from ...utils import log, templates

"""
template_shared_data: create or retrieve shared data used by all configuration templates
"""
TEMPLATE_SHARED_DATA: typing.Optional[dict] = None

def template_shared_data(topology: Box) -> dict:
  global TEMPLATE_SHARED_DATA
  if TEMPLATE_SHARED_DATA is None:
    TEMPLATE_SHARED_DATA = {                      # Create the shared data we need for config templates
      'hostvars': topology.nodes.to_dict(),
      'hosts': get_host_addresses(topology).to_dict(),
      'addressing': topology.addressing.to_dict()
    }

  return TEMPLATE_SHARED_DATA

"""
template_node_data: node data with extra Ansible-like attributes used in config templates or template paths
"""
def template_node_data(n_data: Box, topology: Box) -> dict:
  node_data = adjust_inventory_host(                        # Add group variables to node data
                            node=n_data,
                            defaults=topology.defaults,
                            group_vars=True,
                            template_vars=True).to_dict()
  shared_data = template_shared_data(topology)
  for k,v in shared_data.items():                           # ...copy shared data
    node_data[k] = v

  # ... and add provider info
  node_data['node_provider'] = devices.get_provider(n_data,topology.defaults)
  return node_data

"""
update_template_cache: refresh the node template and check the timestamps on input and output files
"""
def update_template_cache(node: Box, n_provider: str, provider_path: str, topology: Box) -> None:
  t_cache = node.get(f'_template_cache')
  if not t_cache:
    return
  for t_item in t_cache:
    t_path = templates.find_provider_template(
                        node=node,
                        fname=t_item.fname,
                        topology=topology,
                        provider_path=provider_path)
    if not t_path:                                        # Try to find the configuration template
      log.warning(                                        # Houston, we have a problem...
        text=f'Cannot find {t_item.fname} template for node {node.name}/device {node.device}',
        module='initial')
      t_item.fpath = None
      continue

    if t_path != t_item.fpath:                            # Change in configuration template path?
      t_item.fpath = t_path                               # Store the new one and mark the file as modified
      t_item.modified = True
      continue

    if not os.path.exists(t_item.output):                 # Output file missing?
      t_item.modified = True                              # We need to recreate it
      continue

    # Template modified later than the output file? Recreate the output file!
    #
    if os.path.getmtime(t_item.output) < os.path.getmtime(t_item.fpath):
      t_item.modified = True

"""
render_config_template: create an output file from the specified config template
"""
def render_config_template(
      node: Box,
      node_dict: typing.Optional[dict],
      template_id: str,
      template_path: str,
      output_file: str,
      provider_path: str,
      topology: Box) -> bool:

  if node_dict is None:
    node_dict = template_node_data(node,topology)
  try:
    node_paths = templates.config_template_paths(
                    node=node,
                    fname=template_id,
                    topology=topology,
                    provider_path=provider_path)
    templates.write_template(
      in_folder=os.path.dirname(template_path),
      j2=os.path.basename(template_path),
      data=node_dict,
      out_folder=os.path.dirname(output_file),
      filename=os.path.basename(output_file),
      extra_path=node_paths)
    return True
  except Exception as ex:                               # Gee, we failed
    short_path = template_path.replace(str(_files.get_moddir()),'package:')
    log.error(                                          # Report an error and move on
      text=f"Error rendering template {template_id} for node {node.name}/device {node.device}",
      more_data=[f'Template source: {short_path}',f'error: {str(ex)}'] + templates.template_error_location(ex),
      module='initial',
      category=log.IncorrectValue)
    return False
