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
from ...data import get_empty_box
from ...providers import execute_node
from ...utils import log, strings
from .. import _nodeset, ansible, error_and_exit, external_commands, get_message, lab_status_change
from . import configs, utils


def deploy_provider_config(nodeset: list, topology: Box, args: argparse.Namespace) -> typing.Tuple[bool, bool]:
  OK = True
  Used = False

  def deploy_node(n_name: str) -> None:
    n_data = topology.nodes[n_name]
    n_deploy = utils.node_deploy_list(n_data, args)
    if log.VERBOSE:
      log.info(f'Starting deployment thread for {n_name}')
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
def print_internal_stats(topology: Box) -> None:
  print_legend = True
  for n_name, n_data in topology.nodes.items():
    if "_deploy" not in n_data:
      continue
    if print_legend:
      print("Results of configuration script deployments")
      print("=" * strings.rich_width)
      print_legend = False

    failed_list = n_data.get("_deploy.failed", [])
    strings.print_colored_text(f"{n_name:29}", "red" if failed_list else "green")
    n_success = n_data.get("_deploy.success", [])
    if len(n_success):
      if failed_list:
        ok_txt = f"OK: {','.join(n_success)} "
      else:
        ok_txt = f"OK: {len(n_data._deploy.success)} "
      strings.print_colored_text(f"{ok_txt:8}", "green")
    else:
      print(" " * 8, end="")
    if failed_list:
      strings.print_colored_text("Failed: " + ",".join(n_data._deploy.failed), "red")
    print()

  print()


def ansible_extra_vars(topology: Box) -> Box:
  ev = get_empty_box()
  ev.node_files = str(Path("./node_files").resolve().absolute())

  # Change the search names of the module/custom configuration snippet, get rid of config paths
  # and limit the search to per-node node_files
  #
  ev.paths_t_files.files = "{{ config_module }}"
  ev.paths_custom.files = "{{ custom_config }}"
  for p in ["templates", "custom"]:
    ev[f"paths_{p}"].dirs = "{{ node_files }}/{{ inventory_hostname }}"

  # Retain the custom configuration task name(s)
  ev.paths_custom.tasks = topology.defaults.paths.custom.tasks
  return ev


def deploy_ansible_playbook(topology: Box, rest: list) -> bool:
  external_commands.LOG_COMMANDS = True
  rest_args = rest + ["-e", ansible_extra_vars(topology).to_json()]

  return ansible.playbook("initial-config.ansible", rest_args, abort_on_error=False)


def run(topology: Box, args: argparse.Namespace, rest: list) -> None:
  deploy_parts = utils.get_deploy_parts(args)
  deploy_text = ", ".join(deploy_parts) or "complete configuration"

  devices.process_config_sw_check(topology)
  lab_status_change(topology, f"deploying configuration: {deploy_text}")

  nodeset = _nodeset.parse_nodeset(args.limit, topology) if args.limit else list(topology.nodes.keys())
  nodeset = utils.filter_unprovisioned(nodeset, topology)
  if not nodeset:
    error_and_exit("The specified nodeset is empty, there are no nodes to configure")

  if not args.deploy:
    log.info(text="Creating configuration snippets")
    configs.create_node_configs(
      topology=topology,
      nodeset=nodeset,
      abs_path=Path("node_files"),
      args=args,
      skip_extra_config=True,
      node_directory=True,
      default_suffix="none",
    )

  log.exit_on_error()
  (used_internal, status_internal) = deploy_provider_config(nodeset, topology, args)

  if used_internal:
    print()

  ansible_skip_list = utils.nodeset_ansible_skip(nodeset, topology, args)
  if len(ansible_skip_list) != len(nodeset):
    utils.ansible_skip_group(ansible_skip_list)
    if used_internal:
      log.info("Starting Ansible playbook to deploy the rest of the configurations")
    status_ansible = deploy_ansible_playbook(topology, rest)
    utils.ansible_skip_group([])
  else:
    status_ansible = True

  print_internal_stats(topology)

  if not status_internal or not status_ansible:
    error_and_exit("Configuration deployment failed")

  message = get_message(topology, "initial", True)
  if message and not args.no_message:
    print(f"\n{message}")
  elif used_internal:
    print()  # An empty line after internal stats is needed only when there's no lab message

  lab_status_change(topology, f"configuration deployment complete")
