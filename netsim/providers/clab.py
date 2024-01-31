#
# Containerlab provider module
#
import subprocess
import typing
import shutil
from box import Box

from . import _Provider,get_forwarded_ports
from ..utils import log
from ..data import filemaps
from ..cli import is_dry_run,external_commands

def list_bridges( topology: Box ) -> typing.Set[str]:
  return { l.bridge for l in topology.links if l.bridge and l.node_count != 2 and not 'external_bridge' in l.clab }

def use_ovs_bridge( topology: Box ) -> bool:
    return topology.defaults.providers.clab.bridge_type == "ovs-bridge"

def create_linux_bridge( brname: str ) -> bool:
  if external_commands.run_command(
       ['brctl','show',brname],check_result=True,ignore_errors=True) and not is_dry_run():
    log.print_verbose(f'Linux bridge {brname} already exists, skipping')
    return True

  status = external_commands.run_command(
      ['sudo','ip','link','add','name',brname,'type','bridge'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Created Linux bridge '{brname}': {status}" )

  status = external_commands.run_command(
      ['sudo','ip','link','set','dev',brname,'up'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable Linux bridge '{brname}': {status}" )

  status = external_commands.run_command(
      ['sudo','sh','-c',f'echo 65528 >/sys/class/net/{brname}/bridge/group_fwd_mask'],
      check_result=True,
      return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable LLDP,LACP,802.1X forwarding on Linux bridge '{brname}': {status}" )
  return True

def destroy_linux_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ip','link','del','dev',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete Linux bridge '{brname}': {status}" )
  return True

def create_ovs_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','add-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Create OVS bridge '{brname}': {status}" )
  return True

def destroy_ovs_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','del-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete OVS bridge '{brname}': {status}" )
  return True

GENERATED_CONFIG_PATH = "clab_files"

def add_forwarded_ports(node: Box, fplist: list) -> None:
  if not fplist:
    return
  
  node.clab.ports = node.clab.ports or []                       # Make sure the list of forwarded ports is a list
  for port_map in fplist:                                       # Iterate over forwarded port mappings
    port_map_string = f'{port_map[0]}:{port_map[1]}'            # Build the containerlab-compatible map entry
    if not port_map_string in node.clab.ports:                  # ... and add it to the list of forwarded ports
      node.clab.ports.append(port_map_string)                   # ... if the user didn't do it manually

'''
normalize_clab_filemaps: convert clab templates and file binds into host:target lists
'''
def normalize_clab_filemaps(node: Box) -> None:
  for undot_key in ['clab.binds','clab.config_templates']:
    if not undot_key in node:
      continue
    filemaps.normalize_file_mapping(node,f'nodes.{node.name}',undot_key,'clab')

'''
add_daemon_filemaps: add device-level daemon_config dictionary to clab.config_templates dictionary
'''

def add_daemon_filemaps(node: Box, topology: Box) -> None:
  if '_daemon_config' not in node:                # Does the current node need daemon-specific binds?
    return                                        # ... nope, get out of here

  node.clab.config_templates = node.clab.config_templates + node._daemon_config

class Containerlab(_Provider):
  
  def augment_node_data(self, node: Box, topology: Box) -> None:
    node.hostname = "clab-%s-%s" % (topology.name,node.name)
    node_fp = get_forwarded_ports(node,topology)
    if node_fp:
      add_forwarded_ports(node,node_fp)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    add_daemon_filemaps(node,topology)
    normalize_clab_filemaps(node)

    self.create_extra_files_mappings(node,topology)

  def post_configuration_create(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if n.get('clab.binds',None):
        self.create_extra_files(n,topology)

  def pre_start_lab(self, topology: Box) -> None:
    log.print_verbose('pre-start hook for Containerlab - create any bridges')
    for brname in list_bridges(topology):
      if use_ovs_bridge(topology):
        create_ovs_bridge(brname)
      else:
        create_linux_bridge(brname)

  def post_stop_lab(self, topology: Box) -> None:
    log.print_verbose('post-stop hook for Containerlab, cleaning up any bridges')
    for brname in list_bridges(topology):
      if use_ovs_bridge(topology):
        destroy_ovs_bridge(brname)
      else:
        destroy_linux_bridge(brname)
