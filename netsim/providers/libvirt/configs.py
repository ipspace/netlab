"""
Deploy configuration to libvirt nodes using sh/cp_sh config method
"""

import typing

from box import Box

from ...data import append_to_list
from ...utils import log, strings
from ...utils import netmiko as _netmiko
from .. import PRINT_LOCK


def mark_failed(n_data: Box,mod_name: str) -> None:
  append_to_list(n_data._deploy,'failed',mod_name)
  return None

def get_netmiko_connection(n_data: Box, topology: Box, mod_name: str) -> typing.Any:
  if _netmiko.check_netmiko(n_data):
    netmiko_params = _netmiko.prepare_params(n_data,topology)
    if netmiko_params:
      net_connect = _netmiko.connect(n_data,netmiko_params)
      if net_connect:
        return net_connect

  return mark_failed(n_data,mod_name)

def deploy_config(node: Box, topology: Box, deploy_list: list) -> None:
  node_config = node.get('_node_config',None)                 # Do we have modules deployed with internal methods?
  if not node_config:
    return                                                    # Nope? Cool, nothing to do ;)
  
  net_conn: typing.Any = None
  for mod_name,cfg_dest in node_config.items():               # Iterate over internally-deployed modules
    mod_name = mod_name.replace('@','.')                      # Normalize template names with dots
    if mod_name not in deploy_list:
      continue
    if ':' not in cfg_dest:                                   # No config method? Ignore and move on
      continue
    (cfg_file,cfg_method) = cfg_dest.split(':',1)
    if cfg_method not in ['sh','cp_sh']:                      # Not something we could deal with?
      continue                                                # Move on, invalid values should have been caught already

    if not net_conn:                                          # OK, we need a netmiko connection to the device
      net_conn = get_netmiko_connection(node,topology,mod_name)
      if not net_conn:                                        # Failed?
        return                                                # Too bad, the error has been already reported
      try:                                                    # Got the connection, next step: get a root shell
        net_conn.config_mode()
      except Exception as ex:
        log.error(
          f'Cannot get root shell on node {node.name}',
          more_data=[ str(ex) ], module='libvirt', category=log.FatalError)
        return mark_failed(node,mod_name)

    src_file = f"node_files/{node.name}/{mod_name}"
    if log.VERBOSE:
      log.info(f'SCPing {src_file} to {node.name} {cfg_file}')

    try:                                                    # Try to SCP the config script to the node
      import scp  # type: ignore                            # Fails unless you have netmiko installed
      scp_conn = scp.SCPClient(net_conn.remote_conn_pre.get_transport())
      scp_conn.put(src_file,cfg_file)
      scp_conn.close()
    except Exception as ex:
      log.error(
        f'Cannot SCP {src_file} to {node.name}:{cfg_file}',
        more_data=[ str(ex) ], module='libvirt', category=log.FatalError)
      return mark_failed(node,mod_name)

    cmd_marker = "__NETMIKO_RC:"                            # Use a marker to get back the return code
    cmd = f'sh {cfg_file} 2>&1; rc=$?; echo {cmd_marker}$rc'     # ChatGPT-inspired hack. Ugly, but it works
    log.info(f'Executing {mod_name} configuration for node {node.name}')
    output: str = net_conn.send_command(cmd)
    (result,rc) = output.rsplit(cmd_marker,1)               # Get the command printout and the exit code
    rc = rc.split('\n')[0]                                  # Extract the return code from the clutter
    if rc == '0':                                           # All good?
      if log.VERBOSE:                                       # Print the command outputs in verbose mode
        with PRINT_LOCK:
          log.info(f"Results of executing {mod_name} configuration on {node.name}")
          strings.print_colored_text(txt=result,color='green')
      append_to_list(node._deploy,'success',mod_name)       # And mark success
      continue

    with PRINT_LOCK:                                        # We encountered an error
      log.error(
        f'{mod_name} configuration failed for node {node.name}',
        category=log.FatalError,
        skip_header=True,
        module='libvirt')
      if result:                                            # Print command outputs when avaialble
        strings.print_colored_text(txt=result,color='bright_black')

    mark_failed(node,mod_name)
    return
