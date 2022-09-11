#
# Containerlab provider module
#
import subprocess
import typing
import shutil
from box import Box

from . import _Provider
from .. import common
from ..data import get_from_box,must_be_list

def list_bridges( topology: Box ) -> typing.Set[str]:
    return { l.bridge for l in topology.links if l.bridge and l.node_count != 2 }

def use_ovs_bridge( topology: Box ) -> bool:
    return topology.defaults.providers.clab.bridge_type == "ovs-bridge"

def create_linux_bridge( brname: str ) -> bool:
    try:
      result = subprocess.run(['sudo','ip','link','add','name',brname,'type','bridge'],capture_output=True,check=True,text=True)
      common.print_verbose( f"Create Linux bridge '{brname}': {result}" )
      result2 = subprocess.run(['sudo','ip','link','set','dev',brname,'up'],capture_output=True,check=True,text=True)
      common.print_verbose( f"Enable Linux bridge '{brname}': {result2}" )
      result3 = subprocess.run(['sudo','sh','-c',f'echo 65528 >/sys/class/net/{brname}/bridge/group_fwd_mask'],check=True)
      common.print_verbose( f"Enable LLDP,LACP,802.1X forwarding on Linux bridge '{brname}': {result3}" )
      return True
    except Exception as ex:
      print(ex)
      common.error("Error creating bridge '%s': %s" % (brname,ex), module='clab')
      return False

def destroy_linux_bridge( brname: str ) -> bool:
    try:
      result = subprocess.run(['sudo','ip','link','del','dev',brname],capture_output=True,check=True,text=True)
      common.print_verbose( f"Delete Linux bridge '{brname}': {result}" )
      return True
    except Exception as ex:
      print(ex)
      common.error("Error deleting Linux bridge '%s': %s" % (brname,ex), module='clab')
      return False

def create_ovs_bridge( brname: str ) -> bool:
    try:
      result = subprocess.run(['sudo','ovs-vsctl','add-br',brname],capture_output=True,check=True,text=True)
      common.print_verbose( f"Create OVS bridge '{brname}': {result}" )
      return True
    except Exception as ex:
      print(ex)
      common.error("Error deleting OVS bridge '%s': %s" % (brname,ex), module='clab')
      return False

def destroy_ovs_bridge( brname: str ) -> bool:
    try:
      result = subprocess.run(['sudo','ovs-vsctl','del-br',brname],capture_output=True,check=True,text=True)
      common.print_verbose( f"Delete OVS bridge '{brname}': {result}" )
      return True
    except Exception as ex:
      print(ex)
      common.error("Error deleting OVS bridge '%s': %s" % (brname,ex), module='clab')
      return False

GENERATED_CONFIG_PATH = "clab_files"

class Containerlab(_Provider):
  
  def augment_node_data(self, node: Box, topology: Box) -> None:
    node.hostname = "clab-%s-%s" % (topology.name,node.name)

    # For any nodes that have templates for custom configuration files, render them and add bindings
    mappings = get_from_box(node, 'clab.config_templates')
    if mappings:
      cur_binds = get_from_box(node, 'clab.binds') or {}
      for file,mapping in mappings.items():
        if mapping not in cur_binds.values():
          in_folder = f"{ self.get_template_path() }/{node.device}"
          j2 = f"{file}.j2"
          out_folder = f"{GENERATED_CONFIG_PATH}/{node.name}"
          common.write_template( in_folder, j2, node.to_dict(), out_folder, filename=file )
          print( f"Created node configuration file: {out_folder}/{file} based on {in_folder}/{j2}, mapped to {node.name}:{mapping}" )
          node.clab.binds = node.clab.binds or {}
          node.clab.binds += { f"{out_folder}/{file}" : mapping }
        else:
          if common.WARNING:
            print( f"Containerlab warning: Skipping {file}:{mapping}, bind already exists" )

  def pre_start_lab(self, topology: Box) -> None:
    common.print_verbose('pre-start hook for Containerlab - create any bridges')
    for brname in list_bridges(topology):
        if use_ovs_bridge(topology):
            create_ovs_bridge(brname)
        else:
            create_linux_bridge(brname)

  def post_stop_lab(self, topology: Box) -> None:
    common.print_verbose('post-stop hook for Containerlab, cleaning up any bridges')
    for brname in list_bridges(topology):
        if use_ovs_bridge(topology):
            destroy_ovs_bridge(brname)
        else:
            destroy_linux_bridge(brname)

    # Cleanup any generated custom files
    shutil.rmtree(GENERATED_CONFIG_PATH,ignore_errors=True)

