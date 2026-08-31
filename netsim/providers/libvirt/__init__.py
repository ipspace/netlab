#
# Vagrant/libvirt provider module
#

import argparse
import os
import typing

from box import Box

from ...augment import devices
from ...augment.links import get_link_by_index
from ...cli import external_commands
from ...utils import linuxbridge, log, strings
from .. import (
  _Provider,
  add_default_config_mode,
  get_provider_forwarded_ports,
  node_add_forwarded_ports,
  tc_netem_set,
  validate_mgmt_ip,
)
from . import configs, labops, stats


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
      The libvirt links could be modeled as P2P links (using UDP tunnels) or LAN
      links using a Linux bridge. It's better to use the UDP tunnels, but we
      must us the Linux bridge if:

      * The link type is 'lan' or 'stub' (set/used elsewhere, also includes
        hosts connected to links)
      * The libvirt.provider attribute is set (multi-provider links or external
        connectivity)
      * The system defaults say P2P links should be modeled as bridges (used for
        traffic capture)
      * The link or any of the interfaces has the 'tc' parameter

      However, we should never set the link type for virtual links. Currently,
      that would be tunnel and loopback links; cross-provider LAG member links
      don't work (and are thus blocked) and VLAN/SVI links are created later.
      """
      if l.get('type','') in ['tunnel','loopback']:
        continue

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
      labops.pad_node_interfaces(node,topology)
    validate_mgmt_ip(node,required=True,v4only=True,provider='libvirt',mgmt=topology.addressing.mgmt)

    # libvirt does not support provider-specific netlab_config_mode parameter (it can work with 'netmiko),
    # but we have to make it work with "none" device to pass CI/CD integration tests.
    #
    ncm = devices.get_node_group_var(node,'netlab_config_mode',topology.defaults)
    if not ncm:
      return

    if ncm not in topology.defaults.providers.libvirt.config_mode and node.device != 'none':
      log.error(
        f'netlab_config_mode {ncm} does not work with libvirt provider',
        category=log.IncorrectAttr)
      return

    add_default_config_mode(node,topology)

  def transform_node_images(self, topology: Box) -> None:
    self.node_image_version(topology)

  def pre_output_transform(self, topology: Box) -> None:
    _Provider.pre_output_transform(self,topology)
    for link in topology.links:                                     # Adjust links to deal with subprovider gotchas
      lv_data = link.get('libvirt',{})                              # Get libvirt-related link data
      if 'uplink' in lv_data or 'public' in lv_data:                # Is this an uplink?
        labops.check_uplink_name(link)                              # ... check it has a valid interface name
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
    labops.create_vagrant_network(topology)
    labops.create_vagrant_batches(topology)

  def pre_stop_lab(self, topology: Box) -> None:
    log.print_verbose('pre-stop hook for libvirt')
    os.environ["VAGRANT_DEFAULT_PROVIDER"] = "libvirt"              # Force Vagrant to use libvirt as the provider

  def post_start_lab(self, topology: Box) -> None:
    log.print_verbose('libvirt lab has started, fixing Linux bridges')
    mgmt_bridge = labops.get_linux_bridge_name(topology.addressing.mgmt._network or labops.LIBVIRT_MANAGEMENT_NETWORK_NAME)
    if mgmt_bridge:
      topology.addressing.mgmt._bridge = mgmt_bridge

    for l in topology.links:
      brname = l.get('bridge',None)
      if not brname:                                                # Link not using a Linux bridge
        continue
      if not 'libvirt' in l.provider:                               # Not a libvirt link, skip it
        continue

      if log.debug_active('libvirt'):
        print(f'libvirt post_start_lab: fixing Linux bridge {brname} for link {l._linkname}',flush=True)

      linux_bridge = labops.get_linux_bridge_name(brname)
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

  def deploy_node_config(self, node: Box, topology: Box, deploy_list: list) -> None:
    cfg_files = node.get('_node_config',[])
    if not cfg_files:                                          # No node files => no config to deploy here
      return
    configs.deploy_config(node,topology,deploy_list)

  def get_lab_status(self,collect_status: dict) -> Box:
    return stats.get_lab_status(collect_status)

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
