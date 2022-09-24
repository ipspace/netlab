#
# Vagrant/libvirt provider module
#

import subprocess
import re
from box import Box
import pathlib

from .. import common
from . import _Provider

LIBVIRT_MANAGEMENT_NETWORK_NAME = "vagrant-libvirt"
LIBVIRT_MANAGEMENT_NETWORK_FILE = "templates/provider/libvirt/vagrant-libvirt.xml"

def create_vagrant_network() -> None:
  try:
    result = subprocess.run(['virsh','net-info',LIBVIRT_MANAGEMENT_NETWORK_NAME],capture_output=True,text=True)
    if result.returncode == 1:
      # When ret code is 1, the network is missing
      common.print_verbose('creating missing %s network' % LIBVIRT_MANAGEMENT_NETWORK_NAME)
      net_template_xml = pathlib.Path(__file__).parent.parent.joinpath(LIBVIRT_MANAGEMENT_NETWORK_FILE).resolve()
      result2 = subprocess.run(['virsh','net-define',net_template_xml],capture_output=True,check=True,text=True)
  except subprocess.CalledProcessError as e:
    common.error('Exception in net handling for libvirt network %s: [%s] %s' % (LIBVIRT_MANAGEMENT_NETWORK_NAME, e.returncode, e.stderr), module='libvirt')
  return

class Libvirt(_Provider):

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def pre_output_transform(self, topology: Box) -> None:
    for node in topology.nodes.values():
      for intf in node.interfaces:
        if intf.get('linkindex') and not intf.get('virtual_interface'):
          link = topology.links[intf.linkindex - 1]
          if len(link.interfaces) == 2:
            intf.libvirt.type = "tunnel"
            link.pop("bridge",None)
            remote_if_list = [ rif for rif in link.interfaces if rif.node != node.name or rif.ifindex != intf.ifindex ]
            if len(remote_if_list) != 1:
              common.fatal(
                f'Cannot find remote interface for P2P link\n... node {node.name}\n... intf {intf}\n... link {link}\n... iflist {remote_if_list}')
              return

            remote_if = remote_if_list[0]
            intf.remote_ifindex = remote_if.ifindex
            intf.remote_id = topology.nodes[remote_if.node].id
            if not intf.remote_id:
              common.fatal(
                f'Cannot find remote node ID on a P2P link\n... node {node.name}\n... intf {intf}\n... link {link}')
              return

  def pre_start_lab(self, topology: Box) -> None:
    common.print_verbose('pre-start hook for libvirt')
    # Starting from vagrant-libvirt 0.7.0, the destroy actions deletes all the networking
    #  including the "vagrant-libvirt" management network.
    #  Let's re-create it if missing!
    create_vagrant_network()

  def post_start_lab(self, topology: Box) -> None:
    common.print_verbose('libvirt lab has started, fixing Linux bridges')
    for l in topology.links:
      brname = l.get('bridge',None)
      if not brname:
        continue
      try:
        if common.debug_active('libvirt'):
          print('libvirt post_start_lab: fixing Linux bridge for link {l}')
        result = subprocess.run(['virsh','net-info',brname],capture_output=True,check=True,text=True)
      except:
        common.error('Cannot run net-info for libvirt network %s' % brname, module='libvirt')
        continue

      match = None
      if result and result.returncode == 0:
        match = re.search("Bridge:\\s+(.*)$",result.stdout,flags=re.MULTILINE)

      if match:
        common.print_verbose("... network %s maps into %s" % (brname,match.group(1)))
        subprocess.run(['sudo','sh','-c','echo 0x4000 >/sys/class/net/%s/bridge/group_fwd_mask' % match.group(1)],check=True)
        common.print_verbose("... setting LLDP enabled flag on %s" % (match.group(1)))
      else:
        common.error('Cannot get Linux bridge name for libvirt network %s' % brname, module='libvirt')
