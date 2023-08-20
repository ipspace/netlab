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

from ..data import types
from ..utils import log
from ..utils import files as _files
from . import _Provider
from ..augment.links import get_link_by_index
from ..cli import is_dry_run,external_commands

LIBVIRT_MANAGEMENT_NETWORK_NAME  = "vagrant-libvirt"
LIBVIRT_MANAGEMENT_BRIDGE_NAME   = "libvirt-mgmt"
LIBVIRT_MANAGEMENT_TEMPLATE_PATH = "templates/provider/libvirt"
LIBVIRT_MANAGEMENT_TEMPLATE_NAME = "vagrant-libvirt.xml"
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
  search_path = _files.get_search_path("libvirt",LIBVIRT_MANAGEMENT_TEMPLATE_PATH)
  xml_file = _files.find_file(LIBVIRT_MANAGEMENT_TEMPLATE_NAME,search_path)
  if not xml_file:
    log.fatal('Internal error: cannot find {LIBVIRT_MANAGEMENT_TEMPLATE_NAME}')

  return xml_file

def create_network_template(topology: Box) -> str:
  net_template_xml = get_libvirt_mgmt_template()
  if log.debug_active('libvirt'):
    print(f"Template XML: {net_template_xml}")

  mgmt = topology.addressing.mgmt
  try:
    with open(net_template_xml) as xfile:
      xml = xfile.read()
  except Exception as ex:
    log.fatal(f'Cannot open/read XML definition of vagrant-libvirt network {str(sys.exc_info()[1])}')

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
  create_net = True

  if topology is not None and topology.addressing.mgmt._permanent:
    net_list = external_commands.run_command(
      ['virsh','net-list'],check_result=True,return_stdout=True)
    if isinstance(net_list,str):
      create_net = not mgmt_net in net_list
  else:
    if log.debug_active('libvirt'):
      print(f"Deleting libvirt management network {mgmt_net}")
    external_commands.run_command(
      ['virsh','net-destroy',mgmt_net],check_result=True,ignore_errors=True)    # Remove management network
    external_commands.run_command(
      ['virsh','net-undefine',mgmt_net],check_result=True,ignore_errors=True)   # ... if it exists

  if not create_net:
    return

  if not log.QUIET:
    print(f'creating libvirt management network {mgmt_net}')

  if topology is None:
    net_template = get_libvirt_mgmt_template()                    # When called without topology data use the default template
  else:
    net_template = create_network_template(topology)              # Otherwise create a temporary XML file

  external_commands.run_command(
    ['virsh','net-define',net_template],check_result=True)
  if not topology is None:                                        # Remove the temporary XML file if needed
    os.remove(net_template)

  return

def get_linux_bridge_name(virsh_bridge: str) -> typing.Optional[str]:
  if is_dry_run():
    print(f"DRY RUN: Assuming Linux bridge name {virsh_bridge} for libvirt network {virsh_bridge}")
    return virsh_bridge
  result = external_commands.run_command(
    ['virsh','net-info',virsh_bridge],check_result=True,return_stdout=True)
  if not isinstance(result,str):
    log.error('Cannot run net-info for libvirt network %s' % virsh_bridge, module='libvirt')
    return None

  match = None
  match = re.search("Bridge:\\s+(.*)$",result,flags=re.MULTILINE)

  if match:
    return match.group(1)
  else:
    log.error(f'Cannot get Linux bridge name for libvirt network {virsh_bridge}', module='libvirt')

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
  log.exit_on_error()

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
    if not 'links' in topology:
      _Provider.pre_transform(self,topology)
      return

    for l in topology.links:                                     # Set 'uplink' attribute on 'public' links
      if not l.get('libvirt.public',False):                      # Skip links without 'public' attribute
        continue
      if l.get('libvirt.uplink',''):                             # Skip links with 'uplink' attribute
        continue
      l.libvirt.uplink = 'eth0'                                  # Default uplink name is eth0

    _Provider.pre_transform(self,topology)

    for l in topology.links:
      if l.get('libvirt.uplink',None):                           # Set 'public' attribute if the link has an uplink
        if not 'public' in l.libvirt:                            # ... but no 'public' libvirt attr
          l.libvirt.public = 'bridge'                            # ... default mode is bridge (MACVTAP)

      if l.get('libvirt.provider',None):
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

      if 'uplink' in link.libvirt or 'public' in link.libvirt:      # Is this an uplink?
        link.pop('bridge',None)                                     # ... remove bridge name (there's no bridge)

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

        link = get_link_by_index(topology,intf.linkindex)           # Get the link object based on intf linkindex
        if link is None:                                            # Weird, cannot find the link, skip it
          continue

        if not 'libvirt' in link.provider:                          # Not a libvirt link? skip it
          continue

        if 'libvirt' in link:                                       # Do we have libvirt-specific data on the link?
          intf.libvirt = link.libvirt + intf.libvirt                # ... then add it to the interface data
          continue                                                  # ... and move on -- links with libvirt attributes
                                                                    # ... are not tunnels
        if len(link.provider) > 1:                                  # Skip multi-provider links
          continue

        if len(link.interfaces) == 2 and link.type == 'p2p':
          intf.libvirt.type = "tunnel"                              # ... found a true libvirt-only P2P link, set type to tunnel

        if intf.libvirt.get('type') != 'tunnel':                    # The current link is not a tunnel link, move on
          continue

        link.pop("bridge",None)                                     # And now the real work starts. Pop the bridge attribute first

        remote_if_list = [ rif for rif in link.interfaces if rif.node != node.name or rif.ifindex != intf.ifindex ]
        if len(remote_if_list) != 1:                                # There should be only one remote interface attached to this link
          log.fatal(
            f'Cannot find remote interface for P2P link\n... node {node.name}\n... intf {intf}\n... link {link}\n... iflist {remote_if_list}')
          return

        remote_if = remote_if_list[0]                               # Get remote interface
        intf.remote_ifindex = remote_if.ifindex                     # ... and copy its ifindex
        intf.remote_id = topology.nodes[remote_if.node].id          # ... and node ID
        if not intf.remote_id:
          log.fatal(
            f'Cannot find remote node ID on a P2P link\n... node {node.name}\n... intf {intf}\n... link {link}')
          return

  def pre_start_lab(self, topology: Box) -> None:
    log.print_verbose('pre-start hook for libvirt')
    # Starting from vagrant-libvirt 0.7.0, the destroy actions deletes all the networking
    #  including the "vagrant-libvirt" management network.
    #  Let's re-create it if missing!
    os.environ["LIBVIRT_DEFAULT_URI"] = "qemu:///system"            # Create system-wide libvirt networks
    create_vagrant_network(topology)
    create_vagrant_batches(topology)

  def post_start_lab(self, topology: Box) -> None:
    log.print_verbose('libvirt lab has started, fixing Linux bridges')
    mgmt_bridge = get_linux_bridge_name(topology.addressing.mgmt._network or LIBVIRT_MANAGEMENT_NETWORK_NAME)
    if mgmt_bridge:
      topology.addressing.mgmt._bridge = mgmt_bridge

    for l in topology.links:
      brname = l.get('bridge',None)
      if not brname:                                                # Link not using a Linux bridge
        continue
      if not 'libvirt' in l.provider:                               # Not a libvirt link, skip it
        continue

      if log.debug_active('libvirt'):
        print('libvirt post_start_lab: fixing Linux bridge for link {l}')

      linux_bridge = get_linux_bridge_name(brname)
      if linux_bridge is None:
        continue

      l.bridge = linux_bridge
      log.print_verbose(f"... network {brname} maps into {linux_bridge}")
      if not external_commands.run_command(
          ['sudo','sh','-c',f'echo 0x4000 >/sys/class/net/{linux_bridge}/bridge/group_fwd_mask']):
        log.error(f"Cannot set forwarding mask on Linux bridge {linux_bridge}")
        continue

      log.print_verbose(f"... setting LLDP enabled flag on {linux_bridge}")
