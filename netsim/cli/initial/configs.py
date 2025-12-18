"""
Building device configurations in the specified output directory
"""

import argparse
import os
import shutil
import typing
from pathlib import Path

from box import Box

from ...augment import devices
from ...providers import get_provider_module
from ...utils import log, strings
from ...utils import templates as u_templates
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
    log.info(f'Cannot clean a directory outside of the lab directory')

"""
Given the node data and module/template name, create a node config file
"""
def create_config_file(
      node: Box,
      node_dict: dict,
      topology: Box,
      module: str,
      provider_path: str,
      output_path: Path,
      template_path: typing.Optional[str] = None,
      config_mode: str = '') -> bool:

  o_suffix = '.sh' if (config_mode in ('ns','sh')) else '.cfg'
  o_fname = f'{node.name}.{module}{o_suffix}'           # Generate output filename
  if not template_path:
    t_path = u_templates.find_provider_template(        # Find the template path if not specified
              node=node,
              fname=module,
              topology=topology,
              provider_path=provider_path)
  else:
    t_path = template_path

  if not t_path:
    log.error(
      f'Cannot find {module} configuration template for {node.name}/device {node.device}',
      module='configs',
      more_hints=["Use the '--debug template' option if you're troubleshooting custom configuration templates"])
    return False

  OK = i_templates.render_config_template(              # ... node.template.cfg/sh file in the output directory
          node=node,
          node_dict=node_dict,
          template_id=module,
          template_path=t_path,
          output_file=str(output_path / o_fname),
          provider_path=provider_path,
          topology=topology)
  
  if OK and log.VERBOSE:
    log.info(f"Rendered {module} template for {node.name} into {o_fname}")

  return OK

"""
Create all node configuration files, either those specified in the _template_cache
or in the node 'module' or 'config' lists
"""
def create_node_configs(topology: Box, nodeset: list, abs_path: Path, args: argparse.Namespace) -> None:
  all_configs = utils.deploy_all_configs(args)
  for n_name in nodeset:
    n_data = topology.nodes[n_name]

    # Get provider-related node information
    #
    n_provider = devices.get_provider(n_data,topology.defaults)
    p = get_provider_module(topology,n_provider)
    provider_path = p.get_full_template_path()

    # Get other node information
    #
    node_dict = i_templates.template_node_data(n_data,topology)       # The dictionary used in templates
    node_deploy = utils.node_deploy_list(n_data,args)                 # Subset of modules to deploy
    node_module = ['initial'] + n_data.get('module',[])               # All modules used on the node
    node_config = n_data.get('config',[])                             # ...plus the extra configs
    template_cache = n_data[n_provider].get('_template_cache',[])     # Template cache

    template_mode: dict = {}
    if args.generate != 'compare':                                    # Collect config modes for template items
      template_mode = { t_item.fname: t_item.mode for t_item in template_cache if 'mode' in t_item }
    created_list = []

    # Now build the list of items to create
    item_list = [ t_item.fname for t_item in template_cache ]         # Start with template cache
    item_list += [ item for item in node_module + node_config         # Next, add other modules
                          if item not in item_list ]                  # and custom config items
    if not all_configs:                                               # ... and filter the list if needed
      item_list = [ item for item in item_list if item in node_deploy ]

    for module in item_list:
      if create_config_file(
            node=n_data,
            node_dict=node_dict,
            topology=topology,
            module=module,
            provider_path=provider_path,
            output_path=abs_path,
            config_mode=template_mode.get(module,'cfg')):
        created_list.append(module)

    if not log.VERBOSE and created_list:
      strings.print_colored_text(strings.pad_err_code('CREATED',10),'green')
      print(f"{n_name}: {','.join(created_list)}")

"""
Do not generate configuration files that are not module- or custom configs
"""
def remove_extra_templates(topology: Box, nodeset: list) -> None:
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    n_provider = devices.get_provider(n_data,topology.defaults)
    t_cache_key = f'{n_provider}._template_cache' 
    if t_cache_key not in n_data:
      continue

    n_modules = n_data.get('module',[]) + n_data.get('config',[]) + ['initial']
    n_data[t_cache_key] = [ item for item in n_data[t_cache_key] if item.fname in n_modules ]

"""
Create node configurations. The CLI arguments are in 'args' argument, the original
directory in 'cwd' variable (needed to ensure the files are created in a directory
relative to the original cwd)
"""
def run(topology: Box, args: argparse.Namespace, cwd: str) -> None:
  # Find the subset of nodes we should work on
  #
  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())

  abs_path = Path(cwd,args.output).resolve()                # Output directory is relative to starting directory
  if args.clean:                                            # Try to clean it up if asked to do so
    cleanup_config_dir(abs_path, args)

  if cwd != os.getcwd():
    log.info(f'Configuration files will be created in {str(abs_path)}')
  if not abs_path.exists():                                 # Create the output directory if needed
    log.info(f'Creating directory: {args.output}')
    abs_path.mkdir(parents=True,exist_ok=True)

  if args.generate != 'ansible':                            # Did the user ask for Ansible-generated configs?
    if args.generate == 'compare':                          # Do we have to adjust the output to be directly
      remove_extra_templates(topology,nodeset)              # ... comparable with Ansible?
    create_node_configs(topology,nodeset,abs_path,args)
  else:
    ansible.check_version()
    rest = utils.ansible_args(args)
    rest += ['-e',f'config_dir="{abs_path}"' ]              # Add output directory path to Ansible variables
    ansible.playbook('create-config.ansible',rest)

  log.info(f"Initial configurations have been created in the '{args.output}' directory")
