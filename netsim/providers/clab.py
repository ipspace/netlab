#
# Containerlab provider module
#
import argparse
import json
import os
import pathlib
import typing

from box import Box

from ..augment import devices
from ..cli import external_commands, is_dry_run
from ..data import append_to_list, filemaps, get_empty_box
from ..data.types import must_be_dict
from ..utils import linuxbridge, log, strings
from . import (
  READ_ONLY_SUFFIX,
  SHARED_PREFIX,
  SHARED_SUFFIX,
  _Provider,
  get_provider_forwarded_ports,
  node_add_forwarded_ports,
  tc_netem_set,
  validate_mgmt_ip,
)


def list_bridges( topology: Box ) -> typing.Set[str]:
  return { l.bridge for l in topology.links if l.bridge and l.node_count > 2 and not 'external_bridge' in l.clab }

def use_ovs_bridge( topology: Box ) -> bool:
  return topology.defaults.providers.clab.bridge_type == "ovs-bridge"

def create_linux_bridge( brname: str ) -> bool:
  if external_commands.run_command(
       ['brctl','show',brname],check_result=True,ignore_errors=True) and not is_dry_run():
    log.print_verbose(f'Linux bridge {brname} already exists, skipping')
    return True

  status = external_commands.run_command(
      ['sudo','ip','link','add','name',brname,'type','bridge'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Created Linux bridge '{brname}': {status}" )

  status = external_commands.run_command(
      ['sudo','ip','link','set','dev',brname,'up'],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Enable Linux bridge '{brname}': {status}" )

  status = linuxbridge.configure_bridge_forwarding(brname)
  return status

def destroy_linux_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ip','link','del','dev',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete Linux bridge '{brname}': {status}" )
  return True

_OVS_OK: bool = False
def check_ovs_installation() -> None:
  global _OVS_OK
  if _OVS_OK:
    return

  if not external_commands.has_command('ovs-vsctl'):
    log.error(
      'Open vSwitch package is not installed, you cannot use OVS bridges with containerlab',
      more_hints = [
        'This error was caused by defaults.providers.clab.bridge_type being set to ovs-bridge',
        'Use "sudo apt install openvswitch-switch" on Ubuntu or an equivalent command to install Open vSwitch'],
      category=log.FatalError,
      module='clab')
    log.exit_on_error()

  _OVS_OK = True

def create_ovs_bridge( brname: str ) -> bool:
  check_ovs_installation()
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','add-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Create OVS bridge '{brname}': {status}" )
  return True

def destroy_ovs_bridge( brname: str ) -> bool:
  status = external_commands.run_command(
      ['sudo','ovs-vsctl','del-br',brname],check_result=True,return_stdout=True)
  if status is False:
    return False
  log.print_verbose( f"Delete OVS bridge '{brname}': {status}" )
  return True

'''
normalize_clab_filemaps: convert clab templates and file binds into host:target lists
'''
def normalize_clab_filemaps(node: Box) -> None:
  for undot_key in ['clab.binds','clab.config_templates']:
    if not undot_key in node:
      continue
    filemaps.normalize_file_mapping(node,f'nodes.{node.name}',undot_key,'clab')

'''
add_config_filemaps: add device-level node/daemon_config dictionary to clab.config_templates dictionary
'''

def add_config_filemaps(node: Box, topology: Box) -> None:
  skip_config = node.get('skip_config',[])
  for kw in ('_daemon_config','_node_config'):
    if kw not in node:                            # Does the current node need non-ansible binds?
      continue

    # Adjust the configuration templates based on whether the skip_config is set
    #
    if skip_config:
      add_config = { k:v for k,v in node[kw].items() if k not in skip_config }
    else:
      add_config = node[kw]


    # Add the config templates in the correct priority: node config_templates
    # are preferred over _daemon_config which is preferred over _node_config
    # to allow Linux-based daemons to override Linux configuration (for example, routing)
    #
    node.clab.config_templates = add_config + node.clab.config_templates

'''
get_loaded_kernel_modules: Get the list of loaded kernel modules from '/proc/modules'
'''
def get_loaded_kernel_modules() -> list:
  mod_list = pathlib.Path('/proc/modules').read_text().split('\n')
  return [ line.split(' ')[0] for line in mod_list ]

'''
load_kmods: Load kernel modules before starting containers

The kernel modules needed for individual netlab modules are defined in provider- or device 'kmods'
dictionary. If the device 'kmods' value is 'None' then the device uses the standard setup, otherwise
you could specify which kernel modules you want to load.
'''
def load_kmods(topology: Box) -> None:
  defs = topology.defaults
  clab_kmods = defs.providers.clab.kmods
  kmod_list  = get_empty_box()

  for ndata in topology.nodes.values():                     # Iterate over all nodes
    if ndata.get('provider') != 'clab':                     # The node is not using clab provider, move on
      continue
    ddata = devices.get_provider_data(ndata,defs)           # Get device data for the current node
    if 'kmods' not in ddata:                                # Kmods attribute is not there, the device is not using kernel modules
      continue
    must_be_dict(ddata,'kmods',path=f'defaults.devices.{ndata.device}.clab',create_empty=True)
    kdata = clab_kmods + ddata.kmods                        # Merge device-specific modules with system-wide kernel module definition

    # At this point, we have device-specific dictionary mapping netlab modules into kernel modules
    #
    for m in (['initial']+ndata.get('module',[])):          # Now iterate over all the netlab modules the node uses
      if m not in kdata:                                    # ... and if the netlab modules does not need kernel modules
        continue                                            # ... move on
      for kmod in kdata[m]:                                 # Next, add individual kernel modules in the kdata entry
        append_to_list(kmod_list,m,kmod)                    # ... to the module-specific list of kernel mdules

  # Now we have lists of kernel modules that have to be loaded based on netlab modules used in lab topology
  # Next step: for every netlab module, load the missing kernel modules
  #
  for m in kmod_list.keys():
    loaded_kmods = get_loaded_kernel_modules()
    needed_kmods = [ kmod for kmod in kmod_list[m] if kmod not in loaded_kmods ]
    if not needed_kmods:
      continue
    strings.print_colored_text('[LOADING] ','bright_cyan',None)
    print(f'Loading Linux kernel modules {",".join(needed_kmods)} required by containers using {m} module')
    for kmod in needed_kmods:
      status = external_commands.run_command(
        ['sudo','modprobe',kmod ],
        check_result=True,
        return_stdout=True)
      if status is False:
        log.error(f'Cannot load Linux kernel module {kmod}',log.IncorrectValue,'clab')

  log.exit_on_error()

'''
Add node files mapped through 'config_templates' to clab.binds
'''
def add_templates_to_binds(node: Box) -> None:
  if 'clab.config_templates' not in node:
    return
  
  bind_rev  = { item.target:item.source for item in node.get('clab.binds',[]) }
  for t_item in node.clab.config_templates:
    if not t_item.target:
      continue

    if t_item.target in bind_rev:
      log.error(
        f'Cannot map {t_item.source} into {t_item.target} on node {node.name}',
        more_data = [f'The output path is already mapped to {bind_rev[t_item.target]}'],
        category=log.IncorrectValue,
        module='clab')
      continue

    b_item = {'target': t_item.target}
    b_mode = t_item.get('mode','')
    if b_mode == SHARED_SUFFIX:
      b_item['source'] = f'node_files/{SHARED_PREFIX}{t_item.source}'
      b_item['mode'] = READ_ONLY_SUFFIX
    else:
      b_item['source'] = f'node_files/{node.name}/{t_item.source}'
      if b_mode == READ_ONLY_SUFFIX:
        b_item['mode'] = READ_ONLY_SUFFIX

    append_to_list(node.clab,'binds',b_item)

'''
check_node_binds: ensure all files mapped into a container exist
'''
def check_node_binds(node: Box) -> None:
  binds = node.get('clab.binds',[])
  if not binds:
    return

  for bind_item in binds:
    if os.path.exists(bind_item.source):
      continue
    log.error(
      f'File {bind_item.source} mapped to {bind_item.target} on node {node.name} does not exist',
      category=log.IncorrectValue,
      module='clab')

class Containerlab(_Provider):
  
  def augment_node_data(self, node: Box, topology: Box) -> None:
    node.hostname = self.get_node_name(node.name,topology)
    node_fp = get_provider_forwarded_ports(node,topology)
    if node_fp:
      node_add_forwarded_ports(node,node_fp,topology)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    add_config_filemaps(node,topology)
    normalize_clab_filemaps(node)
    validate_mgmt_ip(node,required=True,provider='clab',mgmt=topology.addressing.mgmt)
    add_templates_to_binds(node)

  def post_configuration_create(self, topology: Box) -> None:
    if use_ovs_bridge(topology):
      check_ovs_installation()

    create_node_files = topology.get('_create_node_files',False)
    if not create_node_files:
      return

    for n in topology.nodes.values():
      if devices.get_provider(n,topology.defaults) == 'clab':
        check_node_binds(n)

  def pre_start_lab(self, topology: Box) -> None:
    log.print_verbose('pre-start hook for Containerlab - create any bridges and load kernel modules')
    for brname in list_bridges(topology):
      if use_ovs_bridge(topology):
        create_ovs_bridge(brname)
      else:
        create_linux_bridge(brname)
    load_kmods(topology)

  def post_stop_lab(self, topology: Box) -> None:
    log.print_verbose('post-stop hook for Containerlab, cleaning up any bridges')
    for brname in list_bridges(topology):
      if use_ovs_bridge(topology):
        destroy_ovs_bridge(brname)
      else:
        destroy_linux_bridge(brname)

  def get_lab_status(self) -> Box:
    try:
      status = external_commands.run_command(
                  'docker ps --format json',
                  check_result=True,
                  ignore_errors=True,
                  return_stdout=True,
                  run_always=True)
      
      stat_box = get_empty_box()
      if not isinstance(status,str):
        return stat_box
      try:
        for line in status.split('\n'):
          if not line.startswith('{'):
            continue
          docker_stats = json.loads(line)
          stat_box[docker_stats['Names']].status = docker_stats['Status']
          stat_box[docker_stats['Names']].image = docker_stats['Image']
      except Exception as ex:
        log.error(f'Cannot get Docker status: {ex}',category=log.FatalError,module='clab')
        return stat_box

      return stat_box
    except:
      log.error('Cannot execute "docker ps": {ex}',category=log.FatalError,module='clab')
      return get_empty_box()

  """
  Defines the container host naming convention (globally), this becomes "ansible_host" in Ansible
  and gets added to /etc/hosts for DNS name resolution

  'clab' is the default Containerlab prefix; it can be configured (including setting it to "")
  through "defaults.providers.clab.lab_prefix"
  """
  def get_node_name(self, node: str, topology: Box) -> str:
    n_data = topology.nodes[node]
    if 'clab.name' in n_data:
      return n_data.clab.name

    lab_prefix = topology.get("defaults.providers.clab.lab_prefix")
    return f'{ lab_prefix }-{ topology.name }-{ node }' if lab_prefix else node

  def validate_node_image(self, node: Box, topology: Box) -> None:
    if not getattr(self,'image_cache',None):                # Create an image cache on first call
      self.image_cache: dict = {}

    log.print_verbose(f'clab: validating node {node.name} image {node.box}')
    if node.box in self.image_cache:                        # We already checked this image, move on
      return
    
    docker_image = external_commands.run_command(           # Get image status from Docker
                      ['docker', 'image', 'ls', '--format', 'json', node.box],
                      check_result=True, ignore_errors=True, return_stdout=True)
    self.image_cache[node.box] = docker_image

    if docker_image:                                        # If we got something back, the image is installed
      return
    
    log.print_verbose(f'clab: image {node.box} is not installed: {docker_image}')
    dp_data = devices.get_provider_data(node,topology.defaults)
    if 'build' not in dp_data:                              # We have no build recipe, let's hope it's downloadable
      return

    if dp_data.build is True:
      hints = [
        f"This container image is not available online and has to be installed locally.",
        f"You can build the container image with the 'netlab clab build {node.device}' command",
        f"See https://netlab.tools/netlab/clab/#netlab-clab-build for more details" ]
    else:
      hints = [
        f"This container image is not available online and has to be installed locally.",
        f"If you're using a private Docker repository, use the 'docker image pull {node.box}'",
        f"command to pull the image from it or build/install it using this recipe:",
        dp_data.build ]

    log.error(
      f'Container {node.box} used by node {node.name} is not installed',
      category=log.IncorrectValue,
      module='clab',
      more_hints=hints)

  def deploy_node_config(self, node: Box, topology: Box, deploy_list: list) -> None:
    cfg_files = node.get('clab.config_templates',[])
    if not cfg_files:                                          # No node files => no config to deploy here
      return
    node_name = self.get_node_name(node.name,topology)          # ... get container/namespace name
    for cfg_item in cfg_files:                                  # Go through configuration files
      mod_name = cfg_item.source                                # Get module name
      f_type = cfg_item.get('mode',None)
      if mod_name not in deploy_list:                           # ... and skip it if we're not deploying it
        continue
      config_cmd = None                                         # Command to execute
      if f_type == 'ns':                                        # Is this a host-side script?
        config_cmd = f'sudo ip netns exec {node_name} sh node_files/{node.name}/{mod_name}' 
        log.info(f'Executing {mod_name} configuration for node {node.name} (namespace {node_name})')
      elif f_type == 'sh':
        if not cfg_item.target:
          log.error(
            f'Internal error: bash script for module {mod_name} is not mapped into a container file',
            more_data = [f'node: {node.name} / device: {node.device}'],
            category=log.FatalError,
            module='clab')
          break
        config_cmd = f'docker exec {node_name} sh {cfg_item.target}' # Container-side script
        log.info(f'Executing {mod_name} configuration for node {node.name}')
      if not config_cmd:                                        # Not an executable file?
        continue

      status = external_commands.run_command(
                  config_cmd,                                   # Execute config command
                  ignore_errors=True,
                  check_result=True,                            # Capture stdout
                  return_exitcode=True)                         # and return exit code
      if status == 0:                                           # Everything OK?
        append_to_list(node._deploy,'success',mod_name)
      else:                                                     # Otherwise we failed
        if external_commands.CAPTURED_STDERR:                   # Did we get some printout?
          printout='  '+strings.wrap_error_message(external_commands.CAPTURED_STDERR,indent=2)
          strings.print_colored_text(txt=printout,color='bright_black')
        log.error(
          f'{mod_name} configuration in namespace {node_name} failed for node {node.name}',
          category=log.FatalError,
          more_data=f'Executed command: {config_cmd}',
          skip_header=True,
          module='initial')
        append_to_list(node._deploy,'failed',mod_name)
        break

  def capture_command(self, node: Box, topology: Box, args: argparse.Namespace) -> list:
    cmd = strings.string_to_list(topology.defaults.netlab.capture.command)
    #
    # For some devices, containerlab uses the device interface names for container interface names.
    # However, as Linux doesn't like '/' in device names (one has to wonder why ;), containerlab
    # replaces '/' with '-', so we have to do the same
    #
    cmd = strings.eval_format_list(cmd,{'intf': args.intf.replace('/','-')})
    node_name = self.get_node_name(node.name,topology)
    return strings.string_to_list(f'sudo ip netns exec {node_name}') + cmd

  def set_tc(self, node: Box, topology: Box, intf: Box, error: bool = True) -> None:
    c_name = self.get_node_name(node.name,topology)
    c_intf = intf.get('clab.name',intf.ifname)
    netns = 'sudo ip netns exec ' + c_name
    status = tc_netem_set(intf=c_intf,tc_data=intf.tc,pfx=netns)
    if status is False:
      log.error(
        text=f'Failed to deploy tc policy on {node.name} (container {c_name}) interface {c_intf}',
        module='clab',
        skip_header=True,
        category=log.ErrorAbort)
    elif status:
      log.info(text=f'Traffic control on {node.name} {intf.ifname}:{status}')
