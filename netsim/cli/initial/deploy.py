#
# netlab initial command
#
# Deploys initial device configurations
#
import argparse
import concurrent.futures
import typing
from pathlib import Path

from box import Box

from ... import devices
from ...augment import devices as _a_devices
from ...providers import execute_node
from ...utils import log, strings
from .. import ansible, error_and_exit, external_commands, get_message, is_dry_run, lab_status_change
from . import configs, ready, utils

"""
get_normalize_list -- get a list of all nodes that require normalization step
"""
def get_normalize_list(topology: Box, nodeset: list) -> list:
  normalize_list = []
  defaults = topology.defaults
  for nname,ndata in topology.nodes.items():
    if nname not in nodeset:
      continue
    features = _a_devices.get_device_features(ndata,defaults)
    if features.get('initial.normalize',False):
      normalize_list.append(nname)

  return normalize_list

def deploy_provider_config(nodeset: list, topology: Box, args: argparse.Namespace) -> typing.Tuple[bool, bool]:
  OK = True
  Used = False

  def deploy_node(n_name: str) -> None:
    n_data = topology.nodes[n_name]
    n_deploy = utils.node_deploy_list(n_data, args)
    if not n_deploy:
      return
    deploy_parts=",".join(n_deploy)
    if is_dry_run():
      log.info(f'Would deploy {n_name}: {deploy_parts}',module='dry_run')
      return
    if log.VERBOSE:
      log.info(f'Starting deployment thread for {n_name} to deploy {deploy_parts}')
    execute_node("deploy_node_config", n_data, topology, deploy_list=n_deploy)

  with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(deploy_node, nodeset)

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    Used = Used or "_deploy" in n_data
    OK = OK and "_deploy.failed" not in n_data

  return (Used, OK)

"""
Print the results of the internal script deployments. Has to be called
after the Ansible playbook has completed, or it would be buried deep
into that noise.
"""
def print_internal_stats(topology: Box, top_margin: bool = False) -> None:
  print_legend = True
  max_name_len = max([len(n_name) for n_name in topology.nodes ] + [ 16 ]) + 1
  for n_name, n_data in topology.nodes.items():
    if "_deploy" not in n_data:
      continue
    if print_legend:
      if top_margin:
        print()
      print("Results of configuration script deployments")
      print("=" * strings.rich_width)
      print_legend = False

    failed_list = n_data.get("_deploy.failed", [])
    strings.print_colored_text(f"{n_name.ljust(max_name_len,' ')}", "red" if failed_list else "green")
    first_line = True
    for kw,report,color in [
          ('failed','Failed:  ','red'),
          ('success','Script:  ','green'),
          ('startup','Startup: ','green')]:
      n_result = n_data.get(f"_deploy.{kw}", [])
      if not n_result:
        continue
      if not first_line:
        print(" "*max_name_len,end="")
      first_line = False
      strings.print_colored_text(f"{report}{','.join(n_result)}", color)
      print()

  print()


def execute_ansible_playbook(topology: Box, rest: list, playbook: str) -> bool:
  external_commands.LOG_COMMANDS = True
  extra_vars = ansible.ansible_extra_vars(topology).to_json()
  rest_args = rest + ["-e", extra_vars]

  if is_dry_run():
    log.info(
      f'Would run Ansible playbook {playbook}',
      module='dry_run',
      more_data=[f'args: {rest}', f'extra_vars: {extra_vars}'])
    return True

  return ansible.playbook(playbook, rest_args, abort_on_error=False)

def recreate_configs(topology: Box, args: argparse.Namespace, nodeset: list) -> None:
  if not args.deploy:
    log.section_header('Creating',f'Device configuration snippets')
    configs.create_node_configs(
      topology=topology,
      nodeset=nodeset,
      abs_path=Path("node_files"),
      args=args,
      skip_extra_config=True,
      node_directory=True,
      default_suffix="none",
    )

def deploy_ansible_playbook(
      topology: Box,
      args: argparse.Namespace,
      nodeset: list,
      rest: list,
      deploy_step: str = '') -> typing.Tuple[bool, bool]:
  ansible_skip_list = utils.nodeset_ansible_skip(nodeset, topology, args)
  if len(ansible_skip_list) == len(nodeset):
    return (False,True)

  utils.ansible_skip_group(ansible_skip_list)
  if deploy_step:
    log.info(f"Starting Ansible playbook to {deploy_step} the rest of the configurations")
  playbook = 'normalize-config.ansible' if args.normalize else 'initial-config.ansible'
  status_ansible = execute_ansible_playbook(topology,rest + utils.ansible_args(args),playbook)
  utils.ansible_skip_group([])
  return(True,status_ansible)

def run(topology: Box, args: argparse.Namespace, rest: list) -> None:
  deploy_parts = utils.get_deploy_parts(args)
  if args.normalize:
    deploy_text = "normalize configuration"
  else:
    deploy_text = ", ".join(deploy_parts) or "complete configuration"

  nodeset = utils.get_deploy_nodeset(args,topology)
  if not nodeset:
    error_and_exit("The specified nodeset is empty, there are no nodes to configure")

  normalize_only = args.normalize
  normalize_list = get_normalize_list(topology,nodeset)

  devices.process_config_sw_check(topology)
  recreate_configs(topology,args,nodeset)
  log.exit_on_error()

  ready.run(topology,args,rest)
  log.exit_on_error()

  # Normalize step is executed only if we're deploying complete configuration or if the user
  # asked to run the normalization step or deploy initial configuration
  if normalize_list and (args.normalize or args.initial or utils.deploy_all_configs(args)):
    log.section_header('Config',f'Normalizing device configurations')
    lab_status_change(topology,f'normalizing device configurations')
    args.normalize = True
    (used_internal, status_internal) = deploy_provider_config(normalize_list, topology, args)
    (used_ansible, status_ansible) = deploy_ansible_playbook(topology,args,normalize_list,rest,'normalize' if used_internal else '')
    args.normalize = False

    if not status_ansible or not status_internal or normalize_only:
      print_internal_stats(topology,not used_ansible)

    if not status_ansible or not status_internal:
      error_and_exit('Failed to normalize device configurations')

  if normalize_only:
    if not normalize_list:
      log.warning(text='Lab devices do not need the configuration normalization step',module='initial')
    return

  log.section_header('Config',f'Deploying device configurations')
  lab_status_change(topology, f"deploying configuration: {deploy_text}")
  (used_internal, status_internal) = deploy_provider_config(nodeset, topology, args)
  (used_ansible, status_ansible) = deploy_ansible_playbook(topology,args,nodeset,rest,'deploy' if used_internal else '')

  print_internal_stats(topology,not used_ansible)

  if not status_internal or not status_ansible:
    error_and_exit("Configuration deployment failed")

  message = get_message(topology, "initial", True)
  if message and not args.no_message:
    print(f"\n{message}")
  elif used_internal:
    print()  # An empty line after internal stats is needed only when there's no lab message

  lab_status_change(topology, f"configuration deployment complete")
