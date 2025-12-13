"""
Building device configurations in the specified output directory
"""

import argparse
import shutil
from pathlib import Path

from box import Box

from ...augment import devices
from ...providers import get_provider_module
from ...utils import log
from .. import _nodeset, ansible, error_and_exit
from . import templates as i_templates
from . import utils


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
def create_from_config_templates(topology: Box, nodeset: list, abs_path: Path, args: argparse.Namespace) -> int:
  output_count = 0
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    n_provider = devices.get_provider(n_data,topology.defaults)
    if f'{n_provider}._template_cache' not in n_data:       # The node is not using config templates
      continue                                              # Move on

    p = get_provider_module(topology,n_provider)
    provider_path = p.get_full_template_path()

    # Next, update template cache and iterate over it
    i_templates.update_template_cache(n_data,n_provider,provider_path,topology)
    node_dict = None
    node_deploy = utils.node_deploy_list(n_data,args)
    node_module = n_data.get('module',[])
    node_config = n_data.get('config',[])
    for t_item in n_data[n_provider].get('_template_cache',[]):
      if not t_item.fpath:
        continue

      module = t_item.fname

      OK = module in node_deploy
      OK |= module not in node_module and module not in node_config and 'initial' in node_deploy
      if not OK:
        continue

      if node_dict is None:                                 # Create node data in template-friendly format if needed
        node_dict = i_templates.template_node_data(n_data,topology)

      f_mode = t_item.get('mode','')                        # Figure out the output file name
      o_suffix = '.sh' if f_mode in ('ns','sh') else '.cfg'
      o_fname = f'{n_name}.{t_item.fname}{o_suffix}'        # Try to render the template into
      if i_templates.render_config_template(                # ... node.template.cfg/sh file in the output directory
            node=n_data,
            node_dict=node_dict,
            template_id=module,
            template_path=t_item.fpath,
            output_file=str(abs_path / o_fname),
            provider_path=provider_path,
            topology=topology):
        log.info(f"Rendered {t_item.fname} template for {n_data.name} into {o_fname}")

      output_count += 1

  return output_count

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

  # Create files specified in clab.config_templates directly in the Python code (so they use our
  # internal versions of Jinja2 filters), and run an Ansible playbook to create the rest
  #
  output_count = create_from_config_templates(topology,nodeset,abs_path,args)

  if utils.nodeset_requires_ansible(nodeset,topology,args):
    if output_count:
      print()
      log.info('Starting Ansible to render the rest of the configurations')
    rest = ['-e',f'config_dir="{abs_path}"' ] + rest        # Add output directory path to Ansible variables
    ansible.playbook('create-config.ansible',rest)

  log.info(f"Initial configurations have been created in the '{args.output}' directory")
