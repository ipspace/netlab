#
# netlab config --reload
#
# Reload saved device configurations
#
import argparse
import concurrent.futures
import re
import sys
from pathlib import Path

from box import Box

from ...augment import devices as a_devices
from ...data import get_a_list
from ...utils import log, netmiko
from .. import ansible, error_and_exit, is_dry_run
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

def get_netmiko_nodes(nodeset: list, topology: Box, cfg_path: Path) -> dict:
  """
  Get a dictionary of nodes using netmiko for their configuration replace operation
  """
  defaults = topology.defaults
  nm_nodes: dict = {}

  for n_name in nodeset:
    n_data = topology.nodes[n_name]
    features = a_devices.get_device_features(n_data,defaults)
    nm_cmd = features.get('netmiko.reload.command')
    if not nm_cmd:
      continue

    nm_params = netmiko.prepare_params(n_data,topology)
    if not nm_params:
      continue

    nm_nodes[n_name] = {
      'src': str(next(cfg_path.glob(f'{n_name}.*'))),
      'dst': features.get('netmiko.reload.config','replace-config'),
      'cmd': nm_cmd,
      'ok':  features.get('netmiko.reload.success',None),
      'err': '|'.join(get_a_list(features.get('netmiko.error_regexp'))),
      'ft':  features.get('netmiko.reload.file_transfer',False),
      'cfg': features.get('netmiko.reload.configure',None),
      'params': nm_params }

  return nm_nodes

def reload_with_netmiko(cfg_path: Path, nodeset: list, topology: Box) -> list:
  if netmiko.NETMIKO_IS_MISSING:
    return nodeset

  nm_nodes = get_netmiko_nodes(nodeset,topology,cfg_path)
  if not nm_nodes:
    return nodeset

  def netmiko_scp_replace(n_name: str) -> None:
    try:
      n_data = topology.nodes[n_name]
      nm_data = nm_nodes[n_name]
      if is_dry_run():
        log.info(
          f'I would use netmiko to reload configuration on {n_name}/{n_data.device} but you asked me not to',
          module='reload')
        return

      conn = netmiko.connect(n_data,nm_data['params'])
      if not conn:
        return

      with conn:                                  # Use this to auto-close the connection
        conn.enable()
        if nm_data['cfg']:                        # Extra configuration required?
          conn.send_config_set(nm_data['cfg'])

        if nm_data['ft']:                         # Use netmiko file_transfer function?
          status = netmiko.file_transfer(conn,n_name,nm_data['src'],nm_data['dst'])
        else:
          status = netmiko.scp(conn,n_name,nm_data['src'],nm_data['dst'])
        if not status:
          return

        # Execute the "replace config" command, check its results against known error pattern
        result = conn.send_command(nm_data['cmd'])
        if isinstance(result,list):
          result = '\n'.join(result)
        if not isinstance(result,str):
          raise Exception(f'netmiko send_command returned unexpected results: {type(result)}')
        if nm_data['ok']:
          OK = bool(re.search(nm_data['ok'],result))
        elif nm_data['err']:
          OK = not bool(re.search(nm_data['err'],result))
        else:
          OK = True

        if OK:
          log.info(f'Uploaded and replaced configuration on {n_name}',module='netmiko')
        else:
          log.error(
            f'Failed to replace configuration on {n_name}',
            more_data=result,
            module='netmiko',
            category=log.ErrorAbort,
            skip_header=True)

    except Exception as ex:
      log.error(
        f'Failed to copy/replace configuration for node {n_name}: {ex}',
        more_hints=f'Examine the session log in node_files/{n_name}/netmiko.log',
        category=log.FatalError,
        module='netmiko',
        skip_header=True)

    return

  with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(netmiko_scp_replace, list(nm_nodes))

  return [ n_name for n_name in nodeset if n_name not in nm_nodes ]

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
  nodeset = reload_with_netmiko(cfg_path,nodeset,topology)
  if nodeset:
    run_reload_playbook(topology,nodeset,cfg_path,rest)

  if log.get_error_count():
    sys.exit(1)
