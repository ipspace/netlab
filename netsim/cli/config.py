#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import typing
from pathlib import Path

from box import Box

from ..data import get_box
from ..utils import log
from . import (
  _nodeset,
  ansible,
  error_and_exit,
  external_commands,
  load_snapshot,
  parser_add_debug,
  parser_add_verbose,
  parser_lab_location,
)
from .initial import configs as i_configs
from .initial import utils as i_utils


#
# CLI parser for 'netlab config' command
#
def custom_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
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
    dest='template', action='store',
    help='Configuration template or a directory with templates')
  parser_add_verbose(parser)
  parser_add_debug(parser,add_test=False)
  parser_lab_location(parser,instance=True,action='configure')

  return parser.parse_known_args(args)

def set_initial_args(args: argparse.Namespace, initial: bool = False) -> None:
  setattr(args,'custom',True)                     # Tell 'netlab initial' code to deploy custom configs only
  setattr(args,'initial',initial)                 # We might need initial config for configuration reload
  setattr(args,'module',None)                     # ... but definitely no modules
  setattr(args,'generate',None)                   # ... and internally-generated configs

def set_custom_config(
      topology: Box,
      nodeset: list,
      cfg_name: str,
      extra_vars: dict = {}) -> None:

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    n_data.config = [ cfg_name ]
    for k,v in extra_vars.items():
      n_data[k] = v

def ansible_extra_vars(topology: Box, reload: bool = False, extra_vars: dict = {}) -> Box:
  cfg_sfx = '.cfg' if reload else ''

  ev = get_box(extra_vars)
  ev.node_files = str(Path("./node_files").resolve().absolute())

  ev.paths_t_files.files = "{{ config_module }}" + cfg_sfx    # Take only module file from node_files
  ev.paths_custom.files = "{{ custom_config }}" + cfg_sfx     # And rendered custom config from node_files
  for p in ['templates','custom']:                            # Change the search paths to node_files
    ev[f'paths_{p}'].dirs = "{{ node_files }}/{{ inventory_hostname }}"

  # Retain the custom configuration task name(s)
  ev.paths_custom.tasks = topology.defaults.paths.custom.tasks
  return ev

def get_ansible_args(ans_vars: Box,nodeset: list,cfg_name: str) -> list:
  args = i_utils.common_ansible_args()
  args += ["-e",ans_vars.to_json(),"-e",f'config={cfg_name}']
  args += ["-l",','.join(nodeset)]
  return args

def parse_extra_vars(ev_list: typing.Optional[list]) -> dict:
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

"""
Create the required configs in node_files
"""
def create_node_files(
      topology: Box,
      nodeset: list,
      args: argparse.Namespace,
      cfg_name: str,
      extra_vars: dict = {},
      initial: bool = False,
      cfg_suffix: str = 'none') -> None:

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

"""
Reload node configurations
"""
def reload_node_configs(topology: Box,nodeset: list,args: argparse.Namespace, rest: list) -> None:
  cfg_path = Path(args.template).resolve().absolute()
  if not cfg_path.is_dir():                           # Sanity check: are we reloading from a directory?
    error_and_exit('The argument specified with the --reload option must be a directory')
  
  if args.extra_vars:
    error_and_exit('You cannot specify extra vars while reloading configuration')

  # Warn about devices that should have their configuration reloaded but cannot do that
  #
  no_reload = topology.get('groups.netlab_no_reload.members',[])
  if no_reload:
    dev_list = { topology.nodes[n].device for n in no_reload if n in nodeset }
    if dev_list:
      nodeset = [ n for n in nodeset if n not in no_reload ]
      log.warning(
        text=f"Cannot reload device configurations for device(s) {','.join(sorted(dev_list))}",
        module="reload")
      if not nodeset:
        error_and_exit('Found no nodes that could have their configurations reloaded, exiting')
    else:                                             # No devices affected, set a flag indicating there's
      topology.groups.netlab_no_reload.members = []   # ... no problem (yeah, I know it's a dirty hack)

  no_config = []
  for n_name in nodeset:                              # Identify nodes that have no configs
    if not list(cfg_path.glob(n_name+'.*')):          # ... in the specified directory
      no_config.append(n_name)
  
  if no_config:                                       # Do we have nodes with missing configs?
    log.warning(                                      # Warn the user and adjust the nodeset
      text='Skipping nodes with no saved configurations',
      more_data=[ ",".join(no_config) ],
      module='reload')
    nodeset = [ n for n in nodeset if n not in no_config ]
    if not nodeset:                                   # Any nodes left to work on?
      error_and_exit('Found no nodes with saved configuration, exiting')

  """
  Now prepare the environment for the "netlab initial" processing

  * Limit the custom template search path to the config directory
  * Create initial- and custom config files
  * Change the node "config" parameter to request configuration reload
  """
  topology.defaults.paths.custom.dirs = [ str(cfg_path.parent) ]
  create_node_files(topology,nodeset,args,str(cfg_path.name),initial=True,cfg_suffix='.cfg')

  # Run the Ansible playbook with modified path variables and an adjusted nodeset
  #
  ans_vars = ansible_extra_vars(topology,reload=True)
  rest_args = rest + get_ansible_args(ans_vars,nodeset,str(cfg_path.name))
  if not ansible.playbook('reload-config.ansible',rest_args,abort_on_error=False):
    error_and_exit('Cannot reload initial device configurations')

def deploy_custom_config(topology: Box,nodeset: list,args: argparse.Namespace, rest: list) -> None:
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

  # Run the Ansible playbook with modified path variables and an adjusted nodeset
  #
  ans_vars = ansible_extra_vars(topology,reload=False,extra_vars=extra_vars)
  rest_args = rest + get_ansible_args(ans_vars,nodeset,cfg_name)
  if not ansible.playbook('config.ansible',rest_args,abort_on_error=False):
    error_and_exit('Cannot deploy custom configuration template')

def run_config(cli_args: typing.List[str]) -> None:
  (args,rest) = custom_config_parse(cli_args)
  log.set_logging_flags(args)
  topology = load_snapshot(args)

  nodeset = _nodeset.parse_nodeset(args.limit,topology) if args.limit else list(topology.nodes.keys())
  if not nodeset:
    error_and_exit('The specified nodeset is empty, there are no nodes to configure')
  set_initial_args(args,initial=False)

  if args.reload:
    reload_node_configs(topology,nodeset,args,rest)
  else:
    deploy_custom_config(topology,nodeset,args,rest)

  log.repeat_warnings('netlab config')
  if args.reload and topology.get('groups.netlab_no_reload.members',[]):
    log.info("Use 'netlab initial --limit netlab_no_reload' to deploy initial configuration on"+ \
             " devices that don't support configuration reload")

"""
We need a wrapper around the actual "run" function to catch the user interrupts
"""
def run(cli_args: typing.List[str]) -> None:
  try:
    run_config(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab config')
  return
