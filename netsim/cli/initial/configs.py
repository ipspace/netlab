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
Create all node configuration files, either those specified in the config_templates
or in the node 'module' or 'config' lists
"""
def create_node_configs(
      topology: Box,
      nodeset: list,
      abs_path: Path,
      args: argparse.Namespace,
      skip_extra_config: bool = False,
      node_directory: bool = False,
      default_suffix: typing.Optional[str] = None,
      flatten_output_fname: bool = False) -> None:
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
    node_dict = u_templates.template_node_data(n_data,topology)       # The dictionary used in templates
    node_deploy = utils.node_deploy_list(n_data,args)                 # Subset of modules to deploy
    node_module = ['initial'] + n_data.get('module',[])               # All modules used on the node
    node_config = n_data.get('config',[])                             # ...plus the extra configs

    skip_items :typing.List[str] = []
    config_templates = n_data.get(f'{n_provider}.config_templates',[])
    template_mode = { cfg_item.source:cfg_item.mode for cfg_item in config_templates if 'mode' in cfg_item }
    created_list :typing.List[str] = []

    # Now build the list of items to create
    item_list :typing.List[str] = []
    if not skip_extra_config and args.generate != 'compare':          # Create all files?
      item_list = [ cfg_item.source 
                      for cfg_item in config_templates ]              # Start with template cache

    item_list += [ item for item in node_module + node_config         # Next, add other modules
                          if item not in item_list ]                  # and custom config items
    if not all_configs:                                               # ... and filter the list if needed
      item_list = [ item for item in item_list if item in node_deploy ]

    if skip_items:                                                    # Skip files that have already been created
      item_list = [ item for item in item_list if item not in skip_items ]

    # And just like our life wouldn't be complex enough, we have devices that must do
    # a "normalize" step before initial config, so if 'initial' is in the list of files
    # to create, and we're dealing with such a device, we must prepend 'normalize' to the
    # list of files to create
    if 'initial' in item_list:
      if devices.get_device_attribute(n_data,'features.initial.normalize',topology.defaults):
        item_list = ['normalize'] + item_list

    for module in item_list:
      config_mode = default_suffix or template_mode.get(module,'cfg')
      o_suffix = '' if config_mode == 'none' else '.sh' if (config_mode in ('ns','sh')) else '.cfg'
      if flatten_output_fname:                          # Create all output files in the same directory?
        o_fname = f'{n_name}.{module}{o_suffix}'        # ... we need node name in file name
        o_fname = o_fname.replace('/','.')              # ... and remove the paths
        o_fname = o_fname.replace('.j2.','.')           # ... and the .j2 suffix when present
      else:                                             # Otherwise, create the output file in
        o_fname = f'{n_name}/{module}{o_suffix}'        # ... per node directory
      if u_templates.create_config_file(
            node=n_data,
            node_dict=node_dict,
            topology=topology,
            module=module,
            provider_path=provider_path,
            output_path=abs_path,
            output_file=o_fname):
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
    provider = devices.get_provider(n_data,topology.defaults)
    t_cache_key = f'{provider}.config_templates'
    if t_cache_key not in n_data:
      continue

    n_modules = n_data.get('module',[]) + n_data.get('config',[]) + ['initial']
    n_data[t_cache_key] = [ item for item in n_data[t_cache_key] if item.source in n_modules ]

"""
Create node configurations. The CLI arguments are in 'args' argument, the original
directory in 'cwd' variable (needed to ensure the files are created in a directory
relative to the original cwd)
"""
def run(topology: Box, args: argparse.Namespace, cwd: str) -> None:
  # Find the subset of nodes we should work on
  #
  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())
  nodeset = utils.filter_unprovisioned(nodeset, topology)
  if not nodeset:
    error_and_exit('The specified nodeset is empty, there are no nodes to configure')

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
    create_node_configs(topology,nodeset,abs_path,args,flatten_output_fname=True)
  else:
    ansible.check_version()
    rest = utils.ansible_args(args)
    rest += ['-e',f'config_dir="{abs_path}"' ]              # Add output directory path to Ansible variables
    ansible.playbook('create-config.ansible',rest)

  log.info(f"Initial configurations have been created in the '{args.output}' directory")
