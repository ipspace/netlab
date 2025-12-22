#
# netlab initial command
#
# Deploys initial device configurations
#
import argparse
import os
import typing
from pathlib import Path

from box import Box

from ... import devices
from ...augment import devices as a_devices
from ...data import get_empty_box
from ...providers import execute_node, get_provider_module
from ...utils import log, strings, templates
from .. import _nodeset, ansible, error_and_exit, external_commands, get_message, lab_status_change
from . import configs, utils

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

def update_config_files(topology: Box, nodeset: list) -> None:
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    n_provider = a_devices.get_provider(n_data,topology.defaults)
    p = get_provider_module(topology,n_provider)
    provider_path = p.get_full_template_path()
    update_template_cache(n_data,n_provider,provider_path,topology)

def deploy_provider_config(nodeset: list, topology: Box, args: argparse.Namespace) -> typing.Tuple[bool,bool]:
  OK = True
  Used = False
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    n_deploy = utils.node_deploy_list(n_data,args)
    execute_node('deploy_node_config',n_data,topology,deploy_list=n_deploy)
    Used = Used or '_deploy' in n_data
    OK = OK and '_deploy.failed' not in n_data

  return (Used, OK)

"""
Print the results of the internal script deployments. Has to be called
after the Ansible playbook has completed, or it would be buried deep
into that noise.
"""
def print_internal_stats(topology: Box) -> None:
  print_legend = True
  for n_name,n_data in topology.nodes.items():
    if '_deploy' not in n_data:
      continue
    if print_legend:
      print("Results of configuration script deployments")
      print("=" * strings.rich_width)
      print_legend = False

    failed_list = n_data.get('_deploy.failed',[])
    strings.print_colored_text(f'{n_name:29}','red' if failed_list else 'green')
    n_success = n_data.get('_deploy.success',[])
    if len(n_success):
      if failed_list:
        ok_txt = f'OK: {",".join(n_success)} '
      else:
        ok_txt = f'OK: {len(n_data._deploy.success)} '
      strings.print_colored_text(f'{ok_txt:8}','green')
    else:
      print(' ' * 8,end='')
    if failed_list:
      strings.print_colored_text('Failed: '+','.join(n_data._deploy.failed),'red')
    print()

  print()

def ansible_extra_vars(topology: Box) -> Box:
  ev = get_empty_box()
  ev.node_files = str(Path("./node_files").resolve().absolute())

  ev.paths_t_files.files = "{{ config_module }}"  # Change the name of the module configuration snippet
  ev.paths_custom.files = "{{ custom_config }}"   # Change the name of the custom configuration snippet
  for p in ['templates','custom']:                # Change the search paths of the configuration snippets
    ev[f'paths_{p}'].dirs = "{{ node_files }}/{{ inventory_hostname }}"

  # Retain the custom configuration task name(s)
  ev.paths_custom.tasks = topology.defaults.paths.custom.tasks
  return ev

def deploy_ansible_playbook(topology: Box, rest: list) -> bool:
  external_commands.LOG_COMMANDS = True
  rest_args = rest + ["-e",ansible_extra_vars(topology).to_json()]

  return ansible.playbook('initial-config.ansible',rest_args,abort_on_error=False)

def run(topology: Box, args: argparse.Namespace, rest: list) -> None:
  deploy_parts = utils.get_deploy_parts(args)
  deploy_text = ', '.join(deploy_parts) or 'complete configuration'

  devices.process_config_sw_check(topology)
  lab_status_change(topology,f'deploying configuration: {deploy_text}')

  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())
  if not args.no_refresh:
    log.info(text='Checking for updates in configuration templates')
    update_config_files(topology,nodeset)

  log.info(text='Creating configuration snippets')
  configs.create_node_configs(
    topology=topology,
    nodeset=nodeset,
    abs_path=Path('node_files'),
    args=args,
    no_refresh=args.no_refresh,
    skip_extra_config=True,
    node_directory=True,
    default_suffix='none')

  log.exit_on_error()
  (used_internal, status_internal) = deploy_provider_config(nodeset,topology,args)

  if used_internal:
    print()

  if utils.nodeset_requires_ansible(nodeset,topology,args):
    if used_internal:
      log.info('Starting Ansible playbook to deploy the rest of the configurations')
    status_ansible  = deploy_ansible_playbook(topology,rest)
  else:
    status_ansible = True

  print_internal_stats(topology)

  if not status_internal or not status_ansible:
    error_and_exit('Configuration deployment failed')

  message = get_message(topology,'initial',True)
  if message and not args.no_message:
    print(f"\n{message}")
  elif used_internal:
    print()                   # An empty line after internal stats is needed only when there's no lab message

  lab_status_change(topology,f'configuration deployment complete')
