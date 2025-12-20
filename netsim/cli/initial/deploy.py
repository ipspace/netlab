#
# netlab initial command
#
# Deploys initial device configurations
#
import argparse
import typing

from box import Box

from ... import devices
from ...augment import devices as a_devices
from ...providers import execute_node, get_provider_module
from ...utils import log, strings
from .. import _nodeset, ansible, error_and_exit, external_commands, get_message, lab_status_change
from . import templates as i_templates
from . import utils


def update_config_files(n_data: Box, topology: Box, args: argparse.Namespace) -> None:
  if args.no_refresh:
    return
  n_provider = a_devices.get_provider(n_data,topology.defaults)
  p = get_provider_module(topology,n_provider)
  provider_path = p.get_full_template_path()

  # Next, update template cache and iterate over it
  i_templates.update_template_cache(n_data,n_provider,provider_path,topology)
  node_dict = None

  for t_item in n_data.get('_template_cache',[]):
    if not t_item.get('modified',False):
      continue
    if not t_item.fpath:
      log.warning(
        text=f'Cannot find {t_item.fname} configuration template for node {n_data.name}/device {n_data.device}',
        module='initial')
      continue
    if node_dict is None:                                 # Create node data in template-friendly format if needed
      node_dict = i_templates.template_node_data(n_data,topology)
    if i_templates.render_config_template(                # Recreate configuration file
          node=n_data,
          node_dict=node_dict,
          template_id=t_item.fname,
          template_path=t_item.fpath,
          output_file=t_item.output,
          provider_path=provider_path,
          topology=topology):
      log.warning(
        text=f"{t_item.fname} template for node {n_data.name} changed. Recreated the configuration file")

def deploy_provider_config(nodeset: list, topology: Box, args: argparse.Namespace) -> typing.Tuple[bool,bool]:
  OK = True
  Used = False
  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    update_config_files(n_data,topology,args)
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
    if n_data.get('_deploy.success',0):
      ok_txt = f'OK={n_data._deploy.success}'
      strings.print_colored_text(f'{ok_txt:8}','green')
    else:
      print(' ' * 8,end='')
    if failed_list:
      strings.print_colored_text('Failed: '+','.join(n_data._deploy.failed),'red')
    print()

def deploy_ansible_playbook(rest: list) -> bool:
  external_commands.LOG_COMMANDS = True
  return ansible.playbook('initial-config.ansible',rest,abort_on_error=False)

def run(topology: Box, args: argparse.Namespace, rest: list) -> None:
  deploy_parts = utils.get_deploy_parts(args)
  deploy_text = ', '.join(deploy_parts) or 'complete configuration'

  devices.process_config_sw_check(topology)
  lab_status_change(topology,f'deploying configuration: {deploy_text}')

  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())
  (used_internal, status_internal) = deploy_provider_config(nodeset,topology,args)

  if used_internal:
    print()

  if utils.nodeset_requires_ansible(nodeset,topology,args):
    if used_internal:
      log.info('Starting Ansible playbook to deploy the rest of the configurations')
    status_ansible  = deploy_ansible_playbook(rest)
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
