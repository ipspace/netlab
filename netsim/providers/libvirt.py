#
# Vagrant/libvirt provider module
#

import subprocess
import re
import typing
from box import Box
import pathlib

from .. import common
from ..data import get_from_box
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

def get_linux_bridge_name(virsh_bridge: str) -> typing.Optional[str]:
  try:
    result = subprocess.run(['virsh','net-info',virsh_bridge],capture_output=True,check=True,text=True)
  except:
    common.error('Cannot run net-info for libvirt network %s' % virsh_bridge, module='libvirt')
    return None

  match = None
  if result and result.returncode == 0:
    match = re.search("Bridge:\\s+(.*)$",result.stdout,flags=re.MULTILINE)

  if match:
    return match.group(1)
  else:
    common.error(f'Cannot get Linux bridge name for libvirt network {virsh_bridge}', module='libvirt')

  return None

class Libvirt(_Provider):

  """
  post_transform hook: mark multi-provider links as LAN links
  """
  def pre_transform(self, topology: Box) -> None:
    _Provider.pre_transform(self,topology)
    if not 'links' in topology:
      return

    for l in topology.links:
      if get_from_box(l,'libvirt.provider'):
        l.type = 'lan'
        if not 'bridge' in l:
          l.bridge = "%s_%d" % (topology.name[0:10],l.linkindex)

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def pre_output_transform(self, topology: Box) -> None:
    for link in topology.links:                                     # Adjust links to deal with subprovider gotchas
      if link.type != 'lan':                                        # Multi-provider links are always LAN links
        continue

      if len(link.provider) <= 1:                                   # Skip single-provider links
        continue

      if 'clab' in link.provider:                                   # Find links with clab subprovider
        link.node_count = 999                                       # ... and fake link count to force clab to use a bridge
        if 'libvirt' in link.provider:                              # If the link uses libvirt provider
          link.clab.external_bridge = True                          # ... then the Linux bridge will be create by vagrant-libvirt

    for node in topology.nodes.values():                            # Now find P2P tunnel links and create interface data needed for Vagrantfile
      for intf in node.interfaces:
        if not intf.get('linkindex'):                               # Cannot get interface index, skip it
          continue
        if intf.get('virtual_interface'):                           # Virtual interface, skip it
          continue

        link = topology.links[intf.linkindex - 1]                   # P2P links must have two attached nodes and no extra libvirt attributes
        if not 'libvirt' in link.provider:                          # Not a libvirt link? skip it
          continue

        if len(link.provider) > 1:                                  # multi-provider link. Skip it.
          continue

        if len(link.interfaces) == 2:
          intf.libvirt.type = "tunnel"                              # ... found a true libvirt-only P2P link, set type to tunnel

        if intf.libvirt.type != 'tunnel':                           # The current link is not a tunnel link, move on
          continue

        link.pop("bridge",None)                                     # And now the real work starts. Pop the bridge attribute first

        remote_if_list = [ rif for rif in link.interfaces if rif.node != node.name or rif.ifindex != intf.ifindex ]
        if len(remote_if_list) != 1:                                # There should be only one remote interface attached to this link
          common.fatal(
            f'Cannot find remote interface for P2P link\n... node {node.name}\n... intf {intf}\n... link {link}\n... iflist {remote_if_list}')
          return

        remote_if = remote_if_list[0]                               # Get remote interface
        intf.remote_ifindex = remote_if.ifindex                     # ... and copy its ifindex
        intf.remote_id = topology.nodes[remote_if.node].id          # ... and node ID
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
    mgmt_bridge = get_linux_bridge_name('vagrant-libvirt')
    if mgmt_bridge:
      topology.clab.mgmt.bridge = mgmt_bridge

    for l in topology.links:
      brname = l.get('bridge',None)
      if not brname:                                                # Link not using a Linux bridge
        continue
      if not 'libvirt' in l.provider:                               # Not a libvirt link, skip it
        continue

      if common.debug_active('libvirt'):
        print('libvirt post_start_lab: fixing Linux bridge for link {l}')

      linux_bridge = get_linux_bridge_name(brname)
      if linux_bridge is None:
        continue

      l.bridge = linux_bridge
      common.print_verbose(f"... network {brname} maps into {linux_bridge}")
      try:
        subprocess.run(['sudo','sh','-c',f'echo 0x4000 >/sys/class/net/{linux_bridge}/bridge/group_fwd_mask'],check=True)
      except:
        common.error(f"Cannot set forwarding mask on Linux bridge {linux_bridge}")
        continue
      common.print_verbose(f"... setting LLDP enabled flag on {linux_bridge}")
