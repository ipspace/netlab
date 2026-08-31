"""
Use netmiko instead of Ansible to deploy device configurations
"""
import os

from box import Box

from ...augment import devices as a_devices
from ...data import append_to_list
from ...utils import log
from ...utils import netmiko as _netmiko


def deploy(n_data: Box,topology: Box,n_deploy: list) -> None:
  node_config = n_data.get('_node_config',None)
  if not node_config:
    return

  if not _netmiko.check_netmiko(n_data):
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return

  netmiko_params = _netmiko.prepare_params(n_data,topology)
  if not netmiko_params:
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return None

  net_connect = _netmiko.connect(n_data,netmiko_params)
  if not net_connect:
    append_to_list(n_data._deploy,'failed',n_deploy[0])
    return

  session_log = netmiko_params["session_log"]
  netmiko_err_list = a_devices.get_node_group_var(n_data,'netmiko_error_regexp',topology.defaults)
  netmiko_errors = rf"({'|'.join(netmiko_err_list)})" if isinstance(netmiko_err_list,list) else (netmiko_err_list or "")
  for cfg_item in n_deploy:
    if node_config.get(cfg_item.replace('.','@'),None) != ':netmiko':
      return
    cfg_file = f'node_files/{n_data.name}/{cfg_item}'
    if not os.path.exists(cfg_file):
      log.error(f'Skipping {cfg_item} config on {n_data.name}; cannot find {cfg_file}',category=log.FatalError,module='netmiko')
      append_to_list(n_data._deploy,'failed',cfg_item)
      continue
    try:
      net_connect.send_config_from_file(cfg_file,error_pattern=netmiko_errors)
      log.info(f'Sent {cfg_item} configuration to {n_data.name}',module='netmiko')
      if _netmiko.has_commit(net_connect):
        net_connect.commit()
      if cfg_item in ['normalize','initial']:
        net_connect.set_base_prompt()
      append_to_list(n_data._deploy,'success',cfg_item)
    except Exception as ex:
      append_to_list(n_data._deploy,'failed',cfg_item)
      log.error(
        f'{cfg_item} configuration failed on {n_data.name}',
        more_data=str(ex),
        more_hints=f'Inspect the session log file {session_log} for more details',
        module='netmiko')
      return

  if log.VERBOSE:
    log.info(f"Configuration session log for {n_data.name} is in {session_log}")
