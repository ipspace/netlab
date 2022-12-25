#
# Containerlab provider module
#
import subprocess
import typing
import shutil
from box import Box

from . import _Provider
from .. import common
from ..data import get_from_box

def list_bridges( topology: Box ) -> typing.Set[str]:
  return { l.bridge for l in topology.links if l.bridge and l.node_count != 2 and not 'external_bridge' in l.clab }

def use_ovs_bridge( topology: Box ) -> bool:
    return topology.defaults.providers.clab.bridge_type == "ovs-bridge"

def create_linux_bridge( brname: str ) -> bool:
  try:
    subprocess.run(['brctl','show',brname],capture_output=True,check=True,text=True)
    common.print_verbose(f'Linux bridge {brname} already exists, skipping')
    return True
  except Exception as ex:
    pass

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
    self.create_extra_files_mappings(node,topology)

  def post_configuration_create(self, topology: Box) -> None:
    for n in topology.nodes.values():
      if get_from_box(n,'clab.binds'):
        self.create_extra_files(n,topology)

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
