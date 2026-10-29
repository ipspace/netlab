#
# netlab config --reload
#
# Reload saved device configurations
#
import argparse
from pathlib import Path

from box import Box

from ...augment import devices as a_devices
from ...utils import log
from .. import ansible, error_and_exit
from ..initial import deploy as i_deploy
from ..initial import ready as i_ready
from ..initial import utils as i_utils
from .utils import create_node_files, get_ansible_args


def check_reload_args(args: argparse.Namespace) -> Path:
  """
  Check the 'netlab config --reload' arguments and return the path to the saved configurations
  """
  if args.dry_check:
    error_and_exit('You cannot use --check parameter with --reload')

  cfg_path = Path(args.template).resolve().absolute()
  if not cfg_path.is_dir():                           # Sanity check: are we reloading from a directory?
    error_and_exit('The argument specified with the --reload option must be a directory')
  
  if args.extra_vars:
    error_and_exit('You cannot specify extra vars while reloading configuration')

  return cfg_path

def skip_no_reload_nodes(topology: Box,nodeset: list) -> list:
  """
  Warn about devices that should have their configuration reloaded but cannot do that,
  and remove them from the nodeset.

  When no nodes in the nodeset are affected, empty the netlab_no_reload group to tell
  'run_config' there's no need to tell the user about the nodes that cannot reload configs
  """
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

  return nodeset

def skip_nodes_without_configs(cfg_path: Path,nodeset: list) -> list:
  """
  Remove nodes with no saved configuration in the specified directory from the nodeset
  """
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

  return nodeset

def prepare_devices(topology: Box,nodeset: list) -> None:
  """
  Check that the devices are ready and normalize their configuration (when needed)
  before trying to reload the config
  """
  (ready_args,_) = i_utils.initial_config_parse(['--ready'])
  i_ready.run(topology,ready_args,rest=[],nodeset=nodeset)

  (norm_args,_) = i_utils.initial_config_parse(['--normalize','--deploy','--skip-ready'])
  i_deploy.run(topology,norm_args,rest=[],nodeset=nodeset)

def create_reload_configs(topology: Box,nodeset: list,args: argparse.Namespace,cfg_path: Path) -> None:
  """
  Prepare the environment for the "netlab initial" processing

  * Set the "we're doing initial configuration for reload" node flag
  * Limit the custom template search path to the config directory
  * Create initial- and custom config files
  * Change the node "config" parameter to request configuration reload
  """
  topology.defaults.paths.custom.dirs = [ str(cfg_path.parent) ]
  for n in nodeset:                                   # Change the node parameters for 'create_node_files'
    ndata = topology.nodes[n]
    n_provider = a_devices.get_provider(ndata,topology.defaults)
    ndata.netlab_initial_reload = True                # Set "we're reloading configuration" flag
    ndata.netlab_config_mode = None                   # Fall back to Ansible config mode (we're using Ansible playbook to reload config)
    ndata.pop(f'{n_provider}.config_templates',None)  # And do not generate fancy container configuration files

  create_node_files(topology,nodeset,args,str(cfg_path.name),initial=True,cfg_suffix='.cfg')

def run_reload_playbook(topology: Box,nodeset: list,cfg_path: Path,rest: list) -> None:
  """
  Run the reload-config.ansible playbook with modified path variables and an adjusted nodeset
  """
  ans_vars = ansible.ansible_extra_vars(topology,reload=True)
  rest_args = rest + get_ansible_args(ans_vars,nodeset,str(cfg_path.name))
  if not ansible.playbook('reload-config.ansible',rest_args,abort_on_error=False):
    error_and_exit('Cannot reload initial device configurations')

def reload_node_configs(topology: Box,nodeset: list,args: argparse.Namespace, rest: list) -> None:
  """
  Reload saved node configurations from the specified directory
  """
  cfg_path = check_reload_args(args)
  nodeset = skip_no_reload_nodes(topology,nodeset)
  nodeset = skip_nodes_without_configs(cfg_path,nodeset)
  prepare_devices(topology,nodeset)
  create_reload_configs(topology,nodeset,args,cfg_path)
  run_reload_playbook(topology,nodeset,cfg_path,rest)
