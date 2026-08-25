#
# Vagrant/libvirt provider module
#

import ipaddress
import os
import re
import sys
import tempfile
import typing

from box import Box

from ...augment import devices
from ...cli import external_commands, is_dry_run
from ...data import get_box, types
from ...utils import files as _files
from ...utils import log, strings

LIBVIRT_MANAGEMENT_NETWORK_NAME  = "vagrant-libvirt"
LIBVIRT_MANAGEMENT_BRIDGE_NAME   = "libvirt-mgmt"
LIBVIRT_MANAGEMENT_TEMPLATE_PATH = "templates/provider/libvirt"
LIBVIRT_MANAGEMENT_TEMPLATE_NAME = "vagrant-libvirt.xml"
LIBVIRT_MANAGEMENT_SUBNET       = "192.168.121.0/24"


def replace_xml_mgmt_subnet(topology: Box, xml: str, mgmt: Box, m_subnet: str) -> str:
  """
  Replace management IP subnet in vagrant-libvirt XML template:

  * Replace subnet (.1 address) and netmask
  * Replace start (.2) and end (start -1) of dynamic DHCP range
  * Replace IP addresses in static DHCP bindings (from start until the next address is no longer found)

  Replacements have to match single quotes (in XML) to ensure we don't replace partial IP addresses
  """
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

def get_libvirt_mgmt_template() -> str:
  """
  Create a virsh net-define XML file from vagrant-libvirt XML template:

  * Replace network and bridge name if needed
  * Replace IP subnet/mask and DHCP bindings
  * Create a temporary file with modified XML definitions
  * Return the name of the temporary file
  """
  search_path = _files.get_search_path("libvirt",LIBVIRT_MANAGEMENT_TEMPLATE_PATH)
  xml_file = _files.find_file(LIBVIRT_MANAGEMENT_TEMPLATE_NAME,search_path)
  if not xml_file:
    log.fatal(f'Internal error: cannot find {LIBVIRT_MANAGEMENT_TEMPLATE_NAME}')

  return xml_file

def create_network_template(topology: Box) -> str:
  net_template_xml = get_libvirt_mgmt_template()
  if log.debug_active('libvirt'):
    print(f"Template XML: {net_template_xml}",flush=True)

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
      print(f"Deleting libvirt management network {mgmt_net}",flush=True)
    
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
    print(f'creating libvirt management network {mgmt_net}',flush=True)

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

def pad_node_interfaces(node: Box, topology: Box) -> None:
  """
  pad_node_interfaces: Insert bogus interfaces in the node interface list to cope with the
  required ifindex values.
  """
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

def create_vagrant_batches(topology: Box) -> None:
  """
  Create batches of 'vagrant up' command to deal with very large topologies

  * Split node names into libvirt.batch_size - sized batches
  * Change libvirt.start command into a list of commands
  """
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
