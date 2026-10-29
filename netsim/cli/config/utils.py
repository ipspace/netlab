#
# netlab config utility functions
#
# Argument parsing and shared helpers used by the custom configuration deployment and configuration reload
#
import argparse
import typing
from pathlib import Path

from box import Box

from ...augment import devices as a_devices
from ...utils import log
from .. import (
  error_and_exit,
  parser_add_debug,
  parser_add_verbose,
  parser_lab_location,
)
from ..initial import configs as i_configs
from ..initial import utils as i_utils


def custom_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  """
  CLI parser for 'netlab config' command
  """
  parser = argparse.ArgumentParser(
    prog='netlab config',
    description='Deploy custom configuration template',
    epilog='All other arguments are passed directly to ansible-playbook')
  parser.add_argument(
    '-r','--reload',
    dest='reload',
    action='store_true',
    help='Reload saved device configurations')
  parser.add_argument(
    '-l','--limit',
    dest='limit', action='store',
    help='Limit the operation to a subset of nodes')
  parser.add_argument(
    '-e','--extra-vars',
    dest='extra_vars',action='append',
    help='Specify extra variables for the configuration template')
  parser.add_argument(
    '--dry-run',
    dest='dry_run', action='store_true',
    help='Print actions that would be executed without executing them')
  parser.add_argument(
    '--check',
    dest='dry_check', action='store_true',
    help='Run Ansible playbook in --check mode')
  parser.add_argument(
    dest='template', action='store',
    help='Configuration template or a directory with templates')
  parser_add_verbose(parser)
  parser_add_debug(parser,add_test=False)
  parser_lab_location(parser,instance=True,action='configure')

  return parser.parse_known_args(args)

def set_initial_args(args: argparse.Namespace, initial: bool = False) -> None:
  """
  Set the 'netlab initial' arguments needed to deploy custom configuration templates
  """
  setattr(args,'custom',True)                     # Tell 'netlab initial' code to deploy custom configs only
  setattr(args,'initial',initial)                 # We might need initial config for configuration reload
  setattr(args,'module',None)                     # ... but definitely no modules
  setattr(args,'generate',None)                   # ... internally-generated configs
  setattr(args,'normalize',None)                  # ... or standalone configuration normalization

def set_custom_config(
      topology: Box,
      nodeset: list,
      cfg_name: str,
      extra_vars: dict = {}) -> None:
  """
  Update the configuration deployment data structures with the custom config template
  """

  defaults = topology.defaults
  for n_name in nodeset:
    n_data = topology.nodes[n_name]               # Pretend that the deployed template is the
    n_data.config = [ cfg_name ]                  # ... only custom config template we have
    for k,v in extra_vars.items():                # ... and copy extra vars specified on the command line
      n_data[k] = v                               # ... into node data to be rendered by the template

    # Next, check if the device is using non-ansible configuration mode
    #
    cfg_mode = a_devices.get_node_group_var(n_data,'netlab_config_mode',defaults)
    if not cfg_mode:                              # No "special" config mode?
      continue                                    # ... cool, move on

    if cfg_mode in ['startup']:                   # Cannot use startup configuration hack
      continue
    if cfg_mode == 'sh':                          # sh config mode won't work as we can't map new template into containers
      features = a_devices.get_device_features(n_data,defaults)
      if 'cp_sh' not in features.get('initial.config_mode'):
        continue                                  # Cannot copy into container/VM, use Ansible
      cfg_mode = 'cp_sh'

    cfg_file = ''
    if 'sh' in cfg_mode:                          # Do we have sh/cp_sh config mode?
      cfg_file = a_devices.get_node_group_var(n_data,'netlab_config_path',defaults) or '/etc/cfg-'
      cfg_file += f'custom-{cfg_name}.sh'         # Add file name in the device config directory

    n_data._node_config = { cfg_name.replace('.','@'): cfg_file+':'+cfg_mode }

def get_ansible_args(ans_vars: Box,nodeset: list,cfg_name: str) -> list:
  """
  Build the ansible-playbook arguments (extra vars, config name, node limit)
  """
  args = i_utils.common_ansible_args()
  args += ["-e",ans_vars.to_json(),"-e",f'config={cfg_name}']
  args += ["-l",','.join(nodeset)]
  return args

def parse_extra_vars(ev_list: typing.Optional[list]) -> dict:
  """
  Parse name=value extra variables specified on the command line into a dictionary
  """
  ev: dict = {}
  if not ev_list:
    return ev

  for v_item in ev_list:
    if '=' not in v_item:
      error_and_exit('Extra variables have to be specified in name=value format')
    (n,v)  = v_item.split('=',maxsplit=1)
    try:
      value = eval(v)
    except:
      value = v
    ev[n] = value

  return ev

def create_node_files(
      topology: Box,
      nodeset: list,
      args: argparse.Namespace,
      cfg_name: str,
      extra_vars: dict = {},
      initial: bool = False,
      cfg_suffix: str = 'none') -> None:
  """
  Create the required configs in node_files
  """
  set_initial_args(args,initial=initial)              # Adjust args for 'netlab initial' processing
  set_custom_config(topology,nodeset,cfg_name,extra_vars)

  i_configs.create_node_configs(                      # Create the necessary files in node_files directory
    topology=topology,
    nodeset=nodeset,
    abs_path=Path('node_files'),
    args=args,
    skip_extra_config=True,
    node_directory=True,
    default_suffix=cfg_suffix)
  log.exit_on_error()                                 # Stop if the files could not be created
