#
# Vagrant/libvirt provider module
#

import argparse
import ipaddress
import os
import re
import sys
import tempfile
import typing

from box import Box

from ..augment import devices
from ..augment.links import get_link_by_index
from ..cli import external_commands, is_dry_run
from ..data import get_box, get_empty_box, types
from ..utils import files as _files
from ..utils import linuxbridge, log, strings
from . import _Provider, get_provider_forwarded_ports, node_add_forwarded_ports, tc_netem_set, validate_mgmt_ip

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

def replace_xml_mgmt_subnet(topology: Box, xml: str, mgmt: Box, m_subnet: str) -> str:
  o_net = ipaddress.IPv4Network(m_subnet)
  d_net = ipaddress.IPv4Network(mgmt.ipv4)

  xml = xml.replace(f"'{o_net.netmask}'",f"'{d_net.netmask}'")
  for offset in [1,2]:
    xml = xml.replace(f"'{o_net[offset]}'",f"'{d_net[offset]}'")

  o_start = 100
  d_start = mgmt.start

  xml = xml.replace(f"'{o_net[o_start - 1]}'",f"'{d_net[d_start - 1]}'")
  while True:                               # Replace predefined static DHCP bindings, if any
    o_start += 1
    d_start += 1
    o_addr = str(o_net[o_start])

    if not o_addr in xml:
      break

    xml = xml.replace(f"'{o_addr}'",f"'{d_net[d_start]}'")

  for name,node in topology.nodes.items():  # Add <mac,ip> mapping for each node
    xstring = f"<host mac='{node.mgmt.mac}' ip='{node.mgmt.ipv4}'/>\n<!--more-->"
    xml = xml.replace("<!--more-->",xstring)

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
  except Exception:
    log.fatal(f'Cannot open/read XML definition of vagrant-libvirt network {str(sys.exc_info()[1])}')

  if mgmt._network:
    xml = xml.replace(LIBVIRT_MANAGEMENT_NETWORK_NAME,mgmt._network)

  if mgmt._bridge:
    xml = xml.replace(LIBVIRT_MANAGEMENT_BRIDGE_NAME,mgmt._bridge)

  xml = replace_xml_mgmt_subnet(topology,xml,mgmt,LIBVIRT_MANAGEMENT_SUBNET)

  with tempfile.NamedTemporaryFile(mode='w',delete=False) as tfile:
    tfile.write(xml)
    tfile.close()
    return tfile.name

def create_vagrant_network(topology: typing.Optional[Box] = None) -> None:
  v_status = external_commands.run_command(
      ['vagrant','status','--machine-readable'],check_result=True,ignore_errors=True,return_stdout=True)

  if isinstance(v_status,str) and ('state,running' in v_status):
    log.warning(
      text=f'Vagrant virtual machines are already running, skipping the management network setup')
    return

  mgmt_net = topology.addressing.mgmt._network if topology is not None else ''
  mgmt_net = mgmt_net or LIBVIRT_MANAGEMENT_NETWORK_NAME
  mgmt_br  = topology.addressing.mgmt._bridge if topology is not None else ''
  mgmt_br  = mgmt_br or LIBVIRT_MANAGEMENT_BRIDGE_NAME
  create_net = True

  if topology is not None and topology.addressing.mgmt._permanent:
    net_list = external_commands.run_command(
      ['virsh','net-list'],check_result=True,return_stdout=True)
    if isinstance(net_list,str):
      create_net = not mgmt_net in net_list
  else:
    if log.debug_active('libvirt'):
      print(f"Deleting libvirt management network {mgmt_net}")
    
    # Remove management network if it exists
    external_commands.run_command(
      ['virsh','net-destroy',mgmt_net],check_result=True,ignore_errors=True,return_stdout=True)
    external_commands.run_command(
      ['virsh','net-undefine',mgmt_net],check_result=True,ignore_errors=True,return_stdout=True)
    external_commands.run_command(
      ['sudo','ip','link','delete',mgmt_br],check_result=True,ignore_errors=True,return_stdout=True)

  if not create_net:
    return

  if not log.QUIET:
    strings.print_colored_text('[CREATED] ','green',None)
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

def check_uplink_name(link: Box) -> None:
  ifname = link.get('libvirt.uplink','eth0')
  if is_dry_run():
    print(f"DRY RUN: Assuming interface {ifname} exists")
    return
  
  if not external_commands.run_command(['ip','link','show',ifname],ignore_errors=True,check_result=True):
    log.error(
      f'Uplink interface {ifname} used by {link._linkname} does not exist',
      category=log.IncorrectValue,
      more_hints=[
        'Change the uplink interface name with libvirt.uplink link parameter',
        'Use "ip link show" command to display valid interface names'],
      module='libvirt')

"""
pad_node_interfaces: Insert bogus interfaces in the node interface list to cope with the
required ifindex values.
"""
def pad_node_interfaces(node: Box, topology: Box) -> None:
  phy_iflist = [ intf for intf in node.interfaces if 'virtual_interface' not in intf ]
  vir_iflist = [ intf for intf in node.interfaces if 'virtual_interface' in intf ]
  phy_iflist.sort(key=lambda intf: intf.ifindex)

  dev_data = devices.get_consolidated_device_data(node,topology.defaults)
  ifindex = dev_data.get('ifindex_offset',1)
  ifname_format = dev_data.interface_name
  pad_iflist = []

  while phy_iflist:
    if phy_iflist[0].ifindex > ifindex:

      pad_ifdata = get_box({
        'ifindex': ifindex,
        'type': 'p2p',
        'remote_id': node.id,
        'remote_ifindex': 666,
        'linkindex': 0,
        'neighbors': [],
      })
      pad_ifdata.ifname = strings.eval_format(ifname_format,pad_ifdata)
      pad_iflist.append(pad_ifdata)
    else:
      pad_iflist.append(phy_iflist[0])
      phy_iflist = phy_iflist[1:]

    ifindex = ifindex + 1

  node.interfaces = pad_iflist + vir_iflist
  if 'nic_adapter_count' not in node.libvirt:
    node.libvirt.nic_adapter_count = len(pad_iflist) + 1

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
  node_list = [ n_name for (n_name,n_data) in topology.nodes.items()
                  if devices.get_provider(n_data,topology.defaults) == 'libvirt'
                     and not n_data.get('unmanaged',False) ]

  while True:
    libvirt_defaults.start.append(start_cmd + " " + " ".join(node_list[:batch_size]))     # Add up to batch_size nodes to the start command
    if len(node_list) <= batch_size:
      break
    node_list = node_list[batch_size:]
    if libvirt_defaults.batch_interval:
      libvirt_defaults.start.append(f'sleep {libvirt_defaults.batch_interval}')

class Libvirt(_Provider):

  """
  pre_transform hook: mark multi-provider links as LAN links
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

    p2p_bridge = topology.defaults.get('providers.libvirt.p2p_bridge',False)
    for l in topology.links:
      if l.get('libvirt.uplink',None):                           # Set 'public' attribute if the link has an uplink
        if not 'public' in l.libvirt:                            # ... but no 'public' libvirt attr
          l.libvirt.public = 'bridge'                            # ... default mode is bridge (MACVTAP)

      """
      The libvirt links could be modeled as P2P links (using UDP tunnels) or
      LAN links using a Linux bridge. It's better to use the UDP tunnels, but
      we must us the Linux bridge if:

      * The link type is 'lan' or 'stub' (set/used elsewhere, also includes
        hosts connected to links)
      * The libvirt.provider attribute is set (multi-provider links or external
        connectivity)
      * The system defaults say P2P links should be modeled as bridges
        (used for traffic capture)
      * The link or any of the interfaces has the 'tc' parameter
      """
      must_be_lan = l.get('libvirt.provider',None) and 'vlan' not in l.type
      must_be_lan = must_be_lan or (p2p_bridge and l.get('type','p2p') == 'p2p')
      must_be_lan = must_be_lan or 'tc' in l or [ intf for intf in l.interfaces if 'tc' in intf ]
      if must_be_lan:
        l.type = 'lan'
        if not 'bridge' in l:
          l.bridge = "%s_%d" % (topology.name[0:10],l.linkindex)

  """
  Add default provider forwarded ports to node data
  """
  def augment_node_data(self, node: Box, topology: Box) -> None:
    node_fp = get_provider_forwarded_ports(node,topology)
    if node_fp:
      node_add_forwarded_ports(node,node_fp,topology)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    if node.get('_set_ifindex'):
      pad_node_interfaces(node,topology)
    validate_mgmt_ip(node,required=True,v4only=True,provider='libvirt',mgmt=topology.addressing.mgmt)

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def pre_output_transform(self, topology: Box) -> None:
    _Provider.pre_output_transform(self,topology)
    for link in topology.links:                                     # Adjust links to deal with subprovider gotchas
      lv_data = link.get('libvirt',{})                              # Get libvirt-related link data
      if 'uplink' in lv_data or 'public' in lv_data:                # Is this an uplink?
        check_uplink_name(link)                                     # ... check it has a valid interface name
        link.pop('bridge',None)                                     # ... remove bridge name (there's no bridge)

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

        link = get_link_by_index(topology,intf.linkindex)           # Get the link object based on intf linkindex
        if link is None:                                            # Weird, cannot find the link, skip it
          continue

        if not 'libvirt' in link.provider:                          # Not a libvirt link? skip it
          continue

        if 'bridge' in link:                                        # Copy link bridge name into interface for P2P links
          intf.bridge = link.bridge                                 # that became stubs due to unmanaged node removal

        if 'libvirt' in link:                                       # Do we have libvirt-specific data on the link?
          intf.libvirt = link.libvirt + intf.libvirt                # ... then add it to the interface data
          continue                                                  # ... and move on -- links with libvirt attributes
                                                                    # ... are not tunnels
        if len(link.provider) > 1:                                  # Skip multi-provider links
          continue

        if len(link.interfaces) == 2 and link.type == 'p2p':
          intf.libvirt.type = "tunnel"                              # ... found a true libvirt-only P2P link, set type to tunnel

        if intf.get('libvirt.type') != 'tunnel':                    # The current link is not a tunnel link, move on
          continue

        link.pop("bridge",None)                                     # And now the real work starts. Pop the bridge attribute first

        remote_if_list = [ rif for rif in link.interfaces if rif.node != node.name or rif.ifindex != intf.ifindex ]
        if len(remote_if_list) != 1:                                # There should be only one remote interface attached to this link
          log.error(
            f'Cannot find remote interface for P2P link from node {node.name}',
            more_data=[f'interface: {intf}',f'link: {link}',f'iflist {remote_if_list}'],
            category=log.FatalError,
            module='libvirt')
          return

        remote_if = remote_if_list[0]                               # Get remote interface
        intf.remote_ifindex = remote_if.ifindex                     # ... and copy its ifindex
        intf.remote_id = topology.nodes[remote_if.node].id          # ... and node ID
        if not intf.remote_id:
          log.error(
            f'Cannot find remote node ID on a P2P link from node {node.name}',
            more_data=[f'interface {intf}',f'link {link}'],
            category=log.FatalError,
            module='libvirt')
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
        print(f'libvirt post_start_lab: fixing Linux bridge {brname} for link {l._linkname}')

      linux_bridge = get_linux_bridge_name(brname)
      if linux_bridge is None:
        continue

      l.bridge = linux_bridge
      log.print_verbose(f"... network {brname} maps into {linux_bridge}")
      if not linuxbridge.configure_bridge_forwarding(linux_bridge):
        log.error(f"Cannot set forwarding mask on Linux bridge {linux_bridge}")
        continue
      if not external_commands.run_command(
          ['sudo','sh','-c',f'brctl stp {linux_bridge} off']):
        log.error(f"Cannot disable STP on Linux bridge {linux_bridge}")
        continue
      log.print_verbose(f"... disabled STP on {linux_bridge}")

  def get_lab_status(self) -> Box:
    try:
      status = external_commands.run_command(
                  'vagrant status --machine-readable',
                  check_result=True,
                  ignore_errors=True,
                  return_stdout=True)
      
      stat_box = get_empty_box()
      if not isinstance(status,str):
        return stat_box
      try:
        for line in status.split('\n'):
          items = line.split(',')
          if len(items) >= 4:
            if items[2] == 'state-human-short':
              stat_box[items[1]].status = items[3]
      except Exception as ex:
        log.error(f'Cannot get Vagrant status: {ex}',category=log.FatalError,module='libvirt')
        return stat_box

      return stat_box
    except:
      log.error('Cannot execute "vagrant status --machine-readable": {ex}',category=log.FatalError,module='libvirt')
      return get_empty_box()

  def get_node_name(self, node: str, topology: Box) -> str:
    return f'{ topology.name.split(".")[0] }_{ node }'

  def validate_node_image(self, node: Box, topology: Box) -> None:
    box_list = getattr(self,'box_list',None)
    if not box_list:                                        # Create an box cache on first call
      box_list = external_commands.run_command(             # Get the list of Vagrant boxes
                      ['vagrant', 'box', 'list'],
                      check_result=True, ignore_errors=True, return_stdout=True, run_always=True)
      box_list = box_list if isinstance(box_list,str) else ''
      self.box_list = box_list.split('\n')

    log.print_verbose(f'libvirt: validating node {node.name} image {node.box}')
    box_specs = node.box.split(':')
    box_name = box_specs[0]
    box_version = box_specs[1] if len(box_specs) > 1 else ''

    for box_line in self.box_list:                          # Iterate over Vagrant boxes
      if '(libvirt' not in box_line:                        # Ignore non-libvirt boxes
        continue
      if box_name + ' ' in box_line and box_version + ')' in box_line:
        return                                              # Matching box name and version

    log.print_verbose(f'libvirt: image {node.box} is not installed')
    dp_data = devices.get_provider_data(node,topology.defaults)
    if 'build' not in dp_data:                              # We have no build recipe, let's hope it's downloadable
      return

    log.error(
      f'Vagrant box {node.box} used by node {node.name} is not installed',
      category=log.IncorrectValue,
      module='libvirt',
      more_hints=[ 
        f"This box is not available on Vagrant Cloud and has to be installed locally.",
        f"If you have the Vagrant box available in a private repository, use the",
        f"'vagrant box add <url>' command to add it, or use this recipe to build it:",
        dp_data.build ])

  def get_linux_intf(
        self,
        node: Box,
        topology: Box,
        ifname: str,
        op: str,
        hint: str,
        report_error: bool = True,
        exit_on_error: bool = True) -> typing.Optional[str]:

    intf = [ intf for intf in node.interfaces if intf.ifname == ifname ][0]
    if intf.get('libvirt.type',None) == 'tunnel' or 'bridge' not in intf:
      if report_error:
        log.error(
          f'Cannot perform {op} on libvirt point-to-point links',
          category=log.FatalError,
          module='libvirt',
          skip_header=True,
          exit_on_error=exit_on_error,
          hint=hint)
      return None

    domiflist = external_commands.run_command(
                  ['virsh','domiflist',f'{topology.name}_{node.name}'],
                  check_result=True,
                  return_stdout=True)
    if not isinstance(domiflist,str):
      log.error(
        f'Cannot get the list of libvirt interface for node {node.name}',
        category=log.FatalError,
        module='libvirt',
        skip_header=True,
        exit_on_error=exit_on_error)
      return None

    for intf_line in domiflist.split('\n'):
      intf_data = strings.string_to_list(intf_line)
      if len(intf_data) != 5:
        continue
      if intf_data[2] == intf.bridge:
        return intf_data[0]

    log.error(
      f'Cannot find the interface on node {node.name} attached to libvirt network {intf.bridge}',
      category=log.FatalError,
      module='libvirt',
      skip_header=True,
      exit_on_error=exit_on_error)
    return None

  def capture_command(self, node: Box, topology: Box, args: argparse.Namespace) -> typing.Optional[list]:
    ifname = self.get_linux_intf(node,topology,args.intf,op='packet capture',hint='capture')
    if not ifname:
      return None

    cmd = strings.string_to_list(topology.defaults.netlab.capture.command)
    cmd = strings.eval_format_list(cmd,{'intf': ifname})
    return ['sudo'] + cmd

  def set_tc(self, node: Box, topology: Box, intf: Box, error: bool = True) -> None:
    vm_intf = self.get_linux_intf(
                node,topology,ifname=intf.ifname,
                op='traffic control',hint='tc',report_error=error, exit_on_error=False)
    if not vm_intf:
      return

    status = tc_netem_set(intf=vm_intf,tc_data=intf.tc)
    if status is False:
      log.error(
        text=f'Failed to deploy tc policy on {node.name} interface {intf.ifname} (Linux interface {vm_intf})',
        module='libvirt',
        skip_header=True,
        category=log.ErrorAbort)
    elif status:
      log.info(text=f'Traffic control on {node.name} {intf.ifname}:{status}')
