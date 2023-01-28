#
# Vagrant/libvirt provider module
#

import subprocess
import re
import sys
import os
import typing
from box import Box
import pathlib
import tempfile
import netaddr

from .. import common
from ..data import get_from_box,types
from . import _Provider

LIBVIRT_MANAGEMENT_NETWORK_NAME = "vagrant-libvirt"
LIBVIRT_MANAGEMENT_BRIDGE_NAME  = "libvirt-mgmt"
LIBVIRT_MANAGEMENT_NETWORK_FILE = "templates/provider/libvirt/vagrant-libvirt.xml"
LIBVIRT_MANAGEMENT_SUBNET       = "192.168.121.0/24"

"""
Replace management IP subnet in vagrant-libvirt XML template:

* Replace subnet (.1 address) and netmask
* Replace start (.2) and end (start -1) of dynamic DHCP range
* Replace IP addresses in static DHCP bindings (from start until the next address is no longer found)

Replacements have to match single quotes (in XML) to ensure we don't replace partial IP addresses
"""

def replace_xml_mgmt_subnet(xml: str, mgmt: Box, m_subnet: str) -> str:
  o_net = netaddr.IPNetwork(m_subnet)
  d_net = netaddr.IPNetwork(mgmt.ipv4)

  xml = xml.replace(f"'{o_net.netmask}'",f"'{d_net.netmask}'")
  for offset in [1,2]:
    xml = xml.replace(f"'{o_net[offset]}'",f"'{d_net[offset]}'")

  o_start = 100
  d_start = mgmt.start
  mac_cnt = 0

  xml = xml.replace(f"'{o_net[o_start - 1]}'",f"'{d_net[d_start - 1]}'")
  while True:                                                         # Replace predefined static DHCP bindings
    o_start += 1
    d_start += 1
    mac_cnt += 1
    o_addr = str(o_net[o_start])

    if not o_addr in xml:
      break

    xml = xml.replace(f"'{o_addr}'",f"'{d_net[d_start]}'")

  eui = netaddr.EUI(mgmt.mac)
  while d_start < d_net.size - 2:
    eui[5] = mac_cnt
    xstring = f"<host mac='{str(eui).replace('-',':')}' ip='{d_net[d_start]}'/>\n<!--more-->"
    xml = xml.replace("<!--more-->",xstring)
    d_start += 1
    mac_cnt += 1

  return xml

"""
Create a virsh net-define XML file from vagrant-libvirt XML template:

* Replace network and bridge name if needed
* Replace IP subnet/mask and DHCP bindings
* Create a temporary file with modified XML definitions
* Return the name of the temporary file
"""

def get_libvirt_mgmt_template() -> str:
  return str(pathlib.Path(__file__).parent.parent.joinpath(LIBVIRT_MANAGEMENT_NETWORK_FILE).resolve())

def create_network_template(topology: Box) -> str:
  net_template_xml = get_libvirt_mgmt_template()
  mgmt = topology.addressing.mgmt
  try:
    with open(net_template_xml) as xfile:
      xml = xfile.read()
  except Exception as ex:
    common.fatal(f'Cannot open/read XML definition of vagrant-libvirt network {str(sys.exc_info()[1])}')

  if mgmt._network:
    xml = xml.replace(LIBVIRT_MANAGEMENT_NETWORK_NAME,mgmt._network)

  if mgmt._bridge:
    xml = xml.replace(LIBVIRT_MANAGEMENT_BRIDGE_NAME,mgmt._bridge)

  xml = replace_xml_mgmt_subnet(xml,mgmt,LIBVIRT_MANAGEMENT_SUBNET)

  with tempfile.NamedTemporaryFile(mode='w',delete=False) as tfile:
    tfile.write(xml)
    tfile.close()
    return tfile.name

def create_vagrant_network(topology: typing.Optional[Box] = None) -> None:
  mgmt_net = topology.addressing.mgmt._network if topology is not None else ''
  mgmt_net = mgmt_net or LIBVIRT_MANAGEMENT_NETWORK_NAME
  try:
    subprocess.run(['virsh','net-destroy',mgmt_net],capture_output=True,text=True,check=False)    # Remove management network
    subprocess.run(['virsh','net-undefine',mgmt_net],capture_output=True,text=True,check=False)   # ... if it exists
    common.print_verbose(f'creating libvirt management network {mgmt_net}')

    if topology is None:
      net_template = get_libvirt_mgmt_template()                    # When called without topology data use the default template
    else:
      net_template = create_network_template(topology)              # Otherwise create a temporary XML file
    result2 = subprocess.run(['virsh','net-define',net_template],capture_output=True,check=True,text=True)
    if not topology is None:                                        # Remove the temporary XML file if needed
      os.remove(net_template)

  except subprocess.CalledProcessError as e:
    common.fatal(f'Exception in net handling for libvirt network {mgmt_net}: {e.returncode}\n{e.stderr}')
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

"""
Create batches of 'vagrant up' command to deal with very large topologies

* Split node names into libvirt.batch_size - sized batches
* Change libvirt.start command into a list of commands
"""
def create_vagrant_batches(topology: Box) -> None:
  libvirt_defaults = topology.defaults.providers.libvirt
  if not libvirt_defaults.batch_size:
    return

  types.must_be_int(libvirt_defaults,'batch_size','defaults.providers.libvirt',module='libvirt',min_value=1,max_value=50)
  types.must_be_int(libvirt_defaults,'batch_interval','defaults.providers.libvirt',module='libvirt',min_value=1,max_value=1000)
  common.exit_on_error()

  batch_size = libvirt_defaults.batch_size
  start_cmd  = libvirt_defaults.start
  libvirt_defaults.start = []
  node_list = list(topology.nodes.keys())

  while True:
    libvirt_defaults.start.append(start_cmd + " " + " ".join(node_list[:batch_size]))     # Add up to batch_size nodes to the start command
    if len(node_list) <= batch_size:
      break
    node_list = node_list[batch_size:]
    if libvirt_defaults.batch_interval:
      libvirt_defaults.start.append(f'sleep {libvirt_defaults.batch_interval}')

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
    _Provider.pre_output_transform(self,topology)
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
        if not intf.get('linkindex',None):                          # Cannot get interface index, skip it
          continue
        if intf.get('virtual_interface',None):                      # Virtual interface, skip it
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
    create_vagrant_network(topology)
    create_vagrant_batches(topology)

  def post_start_lab(self, topology: Box) -> None:
    common.print_verbose('libvirt lab has started, fixing Linux bridges')
    mgmt_bridge = get_linux_bridge_name(topology.addressing.mgmt._network or LIBVIRT_MANAGEMENT_NETWORK_NAME)
    if mgmt_bridge:
      topology.addressing.mgmt._bridge = mgmt_bridge

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
