"""
Building device configurations in the specified output directory
"""

import argparse
import os
import shutil
from pathlib import Path

from box import Box

from ... import data
from ...augment import devices
from ...outputs.ansible import get_host_addresses
from ...outputs.common import adjust_inventory_host
from ...providers import _Provider
from ...utils import log, templates
from .. import _nodeset, ansible, error_and_exit


def cleanup_config_dir(output_path: Path, args: argparse.Namespace) -> None:
  if not output_path.exists():                      # Doesn't exist? No problem, no cleanup
    return

  cur_dir = Path('.').resolve()                     # Check if the output path is within current directory
  if output_path == cur_dir:
    error_and_exit('Cannot cleanup current directory')

  try:
    output_path.relative_to(cur_dir)                # Is it relative to .?
    log.info(f"Cleaning up the '{args.output}' directory")
    try:
      shutil.rmtree(output_path)
    except Exception as ex:
      log.error(f"Failed to remove directory '{args.output}'",more_data=[ str(ex) ])
  except ValueError:
    log.info(f'Cannot clean a directory outside of the current directory')

"""
Create files that are usually created for clab.binds from clab.config_templates
in the config directory to have everything in one place
"""
def create_from_config_templates(topology: Box, nodeset: list, abs_path: Path, args: argparse.Namespace) -> None:
  shared_data = {                                           # Create the shared data we need for config templates
    'hostvars': topology.nodes.to_dict(),
    'hosts': get_host_addresses(topology),
    'addressing': topology.addressing.to_dict()
  }

  output_path = str(abs_path)
  all_configs = not args.module and not args.initial and not args.custom

  # Get the (optional) list of modules for which we're rendering the configs
  #
  mod_list = topology.get('module',[]) if args.module == '*' or not args.module else args.module.split(',')
  if args.initial:
    mod_list = mod_list + [ 'initial' ]

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    if 'clab.config_templates' not in n_data:               # The node is not using config templates
      continue                                              # Move on

    p = _Provider(provider=devices.get_provider(n_data,topology.defaults),data=data.get_empty_box())
    node_data = adjust_inventory_host(                      # Add group variables to node data
                              node=n_data,
                              defaults=topology.defaults,
                              group_vars=True).to_dict()
    for k,v in shared_data.items():                         # And copy shared data
      node_data[k] = v

    node_data['node_provider'] = devices.get_provider(n_data,topology.defaults)
    for b_item in n_data.clab.config_templates:             # Now iterate over all config templates the node is using
      b_template = b_item.split(':')[0].replace('@','.')    # Extract template name
      if not all_configs:                                   # Check whether the user wants us to generate this file
        skip = mod_list and b_template not in mod_list      # Skip modules that are not in mod_list
        skip = skip or args.custom and b_template not in n_data.get('config',[])
        if skip:                                            # ... or custom configs not in 'config' list
          continue
      b_path = p.find_extra_template(n_data,b_template,topology)
      if not b_path:                                        # Try to find the configuration template
        log.warning(                                        # Houston, we have a problem...
          text=f'Cannot find template {b_template} for node {n_name}/device {n_data.device}',
          module='initial')
        continue

      try:
        node_paths = p.extra_template_paths(n_data,topology,b_template)
        o_fname = f'{n_name}.{b_template}.cfg'              # Try to render the template into
        templates.write_template(                           # ... node.template.cfg file in the output directory
          in_folder=os.path.dirname(b_path),
          j2=os.path.basename(b_path),
          data=node_data,
          out_folder=output_path,
          filename=o_fname,
          extra_path=node_paths)
        log.info(f"Rendered {b_template} template for {n_name} into {o_fname}")
      except Exception as ex:                               # Gee, we failed
        log.error(                                          # Report an error and move on
          text=f"Error rendering template {b_template} for node {n_name}/device {n_data.device}",
          more_data=[f'Template source: {b_path}',f'error: {str(ex)}'],
          module='initial',
          category=log.IncorrectValue)

"""
Create node configurations

The Ansible parameters are already parsed/augmented and received in the 'rest' list
"""
def run(topology: Box, args: argparse.Namespace, rest: list) -> None:
  # Find the subset of nodes we should work on
  #
  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())

  abs_path = Path(args.output).resolve()                    # Output directory could be outside lab directory
  if args.clean:                                            # Try to clean it up if asked to do so
    cleanup_config_dir(abs_path, args)

  if not abs_path.exists():                                 # Create the output directory if needed
    log.info(f'Creating directory: {args.output}')
    abs_path.mkdir(parents=True,exist_ok=True)

  rest = ['-e',f'config_dir="{abs_path}"' ] + rest          # Add output directory path to Ansible variables

  # Create files specified in clab.config_templates directly in the Python code (so they use our
  # internal versions of Jinja2 filters), and run an Ansible playbook to create the rest
  #
  create_from_config_templates(topology,nodeset,abs_path,args)
  ansible.playbook('create-config.ansible',rest)
  log.info(f"Initial configurations have been created in the '{args.output}' directory")
