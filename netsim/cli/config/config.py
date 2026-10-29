#
# netlab config <template>
#
# Deploy custom configuration template to network devices
#
import argparse
from pathlib import Path

from box import Box

from .. import ansible, error_and_exit
from ..initial import deploy as i_deploy
from ..initial import utils as i_utils
from .utils import create_node_files, get_ansible_args, parse_extra_vars


def config_ansible_playbook(cfg_name: str,nodeset: list,topology: Box,extra_vars: dict, rest: list) -> bool:
  """
  Run the config.ansible playbook with modified path variables and an adjusted nodeset
  """
  #
  ans_vars = ansible.ansible_extra_vars(topology,reload=False,extra_vars=extra_vars)
  rest_args = rest + get_ansible_args(ans_vars,nodeset,cfg_name)
  return ansible.playbook('config.ansible',rest_args,abort_on_error=False)

def deploy_custom_config(topology: Box,nodeset: list,args: argparse.Namespace, rest: list) -> None:
  """
  Deploy a custom configuration template using internal deployment mechanisms or Ansible
  """
  cfg_name = args.template
  if '/' in cfg_name:                             # Custom config specified as a path to directory
    cfg_path = Path(cfg_name).absolute().resolve()
    if not cfg_path.exists():                     # Does the specified path exist?
      error_and_exit(f'The path {cfg_name} does not exist')

    topology.defaults.paths.custom.dirs = [ str(cfg_path.parent) ]
    cfg_name = str(cfg_path.name)
    if cfg_name.endswith('.j2'):
      cfg_name = cfg_name[:-3]

  extra_vars=parse_extra_vars(args.extra_vars)
  create_node_files(topology,nodeset,args,cfg_name,extra_vars)

  (deploy_args,_) = i_utils.initial_config_parse(['--custom'])
  if not args.dry_check:
    (used_internal, config_status) = i_deploy.deploy_internal_config(nodeset,topology,deploy_args)
  else:
    (used_internal, config_status) = (False, True)
    rest += ['--check']

  if used_internal:
    ansible_nodeset = [ n for n in nodeset if '_deploy' not in topology.nodes[n] ]
  else:
    ansible_nodeset = nodeset

  if ansible_nodeset:
    ansible_status = config_ansible_playbook(cfg_name,ansible_nodeset,topology,extra_vars,rest)
    config_status = config_status and ansible_status
    print()

  i_deploy.print_internal_stats(topology,not bool(ansible_nodeset))
  if not config_status:
    error_and_exit('Custom configuration deployment failed')
