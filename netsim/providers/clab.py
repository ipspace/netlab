#
# Containerlab provider module
#
import subprocess
from box import Box

from . import _Provider
from .. import common

class Containerlab(_Provider):

  def augment_node_data(self, node: Box, topology: Box) -> None:
    node.hostname = "clab-%s-%s" % (topology.name,node.name)

  def pre_start_lab(self, topology: Box) -> None:
    common.print_verbose('pre-start hook for Containerlab')
    for l in topology.links:
      brname = l.get('bridge',None)
      if brname:
        try:
          result = subprocess.run(['sudo','ip','link','add','name',brname,'type','bridge'],capture_output=True,check=True,text=True)
          common.print_verbose( f"Create Linux bridge '{brname}': {result}" )
          result2 = subprocess.run(['sudo','ip','link','set','dev',brname,'up'],capture_output=True,check=True,text=True)
          common.print_verbose( f"Enable Linux bridge '{brname}': {result2}" )
        except Exception as ex:
          print(ex)
          common.error("Error creating bridge '%s': %s" % (brname,ex), module='clab')
          continue

  def post_stop_lab(self, topology: Box) -> None:
    common.print_verbose('post-stop hook for Containerlab, cleaning up any bridges')
    for l in topology.links:
      brname = l.get('bridge',None)
      if brname:
        try:
          result = subprocess.run(['sudo','ip','link','del','dev',brname],capture_output=True,check=True,text=True)
          common.print_verbose( f"Delete Linux bridge '{brname}': {result}" )
        except Exception as ex:
          print(ex)
          common.error("Error deleting bridge '%s': %s" % (brname,ex), module='clab')
          continue
