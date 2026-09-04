#
# Containerlab provider module
#
import argparse
import json

from box import Box

from ...augment import devices
from ...cli import external_commands
from ...data import append_to_list, filemaps, get_empty_box
from ...utils import log, strings
from .. import (
  READ_ONLY_SUFFIX,
  SHARED_PREFIX,
  SHARED_SUFFIX,
  _Provider,
  add_default_config_mode,
  get_provider_forwarded_ports,
  node_add_forwarded_ports,
  tc_netem_set,
  validate_mgmt_ip,
)
from . import binds, configs, labops, utils


class Containerlab(_Provider):
  
  def augment_node_data(self, node: Box, topology: Box) -> None:
    if node.name in topology.defaults.providers.clab.reserved_names:
      log.error(
        f'Node name {node.name} cannot be used with clab provider',
        category=log.IncorrectValue)
      return

    node.hostname = self.get_node_name(node.name,topology)
    node_fp = get_provider_forwarded_ports(node,topology)
    if node_fp:
      node_add_forwarded_ports(node,node_fp,topology)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    utils.add_clab_exec(node,'netlab_start_exec',topology)
    configs.set_node_config_targets(node,topology)
    if add_default_config_mode(node,topology):                        # Are we using internal config mechanisms?
      utils.add_clab_exec(node,'netlab_config_exec',topology)         # ... in that case, maybe the device needs extra start commands
    binds.add_config_filemaps(node,topology)
    binds.normalize_clab_filemaps(node)
    validate_mgmt_ip(node,required=True,provider='clab',mgmt=topology.addressing.mgmt)
    binds.add_templates_to_binds(node)
    configs.add_startup_config(node)

  def post_configuration_create(self, topology: Box) -> None:
    if labops.use_ovs_bridge(topology):
      labops.check_ovs_installation()

    for n in topology.nodes.values():
      if devices.get_provider(n,topology.defaults) != 'clab':
        continue
      binds.check_node_binds(n)
      configs.generate_startup_config(n)

  def pre_start_lab(self, topology: Box) -> None:
    log.print_verbose('pre-start hook for Containerlab - create any bridges and load kernel modules')
    labops.set_clab_runtime(topology)

    for brname in utils.list_bridges(topology):
      if labops.use_ovs_bridge(topology):
        labops.create_ovs_bridge(brname)
      else:
        labops.create_linux_bridge(brname)
    labops.load_kmods(topology)

  def pre_stop_lab(self, topology: Box) -> None:
    labops.set_clab_runtime(topology)

  def post_stop_lab(self, topology: Box) -> None:
    log.print_verbose('post-stop hook for Containerlab, cleaning up any bridges')
    for brname in utils.list_bridges(topology):
      if labops.use_ovs_bridge(topology):
        labops.destroy_ovs_bridge(brname)
      else:
        labops.destroy_linux_bridge(brname)

  def get_lab_status(self,collect_status: dict) -> Box:
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
        status_str = status.strip()
        if status_str.startswith('['):                        # Podman: normalize array to one-object-per-line
          status_str = '\n'.join(
            json.dumps({**item, 'Names': item['Names'][0] if isinstance(item.get('Names'), list) else item.get('Names','')})
            for item in json.loads(status_str))

        for line in status_str.split('\n'):
          if not line.startswith('{'):
            continue
          docker_stats = json.loads(line)
          stat_box[docker_stats['Names']].status = docker_stats.get('Status','')
          stat_box[docker_stats['Names']].image = docker_stats.get('Image','')
      except Exception as ex:
        log.error(f'Cannot get Docker status: {ex}',category=log.FatalError,module='clab')
        return stat_box

      if collect_status.get('memory',False):
        self.add_memory_usage(stat_box)

      return stat_box
    except Exception as ex:
      log.error(f'Cannot execute "docker ps": {ex}',category=log.FatalError,module='clab')
      return get_empty_box()

  """
  Add the current memory usage of running containers to the lab status data. 'docker stats'
  reports the memory usage as 'used / limit'; we're interested only in the 'used' part.

  Failures are non-fatal -- memory usage is extra information, not a prerequisite for
  displaying the lab status.
  """
  def add_memory_usage(self, stat_box: Box) -> None:
    try:
      stats = external_commands.run_command(
                  'docker stats --no-stream --format json',
                  check_result=True,
                  ignore_errors=True,
                  return_stdout=True,
                  run_always=True)
    except Exception as ex:
      log.print_verbose(f'Cannot execute "docker stats": {ex}')
      return

    if not isinstance(stats,str):
      return

    try:
      stats_str = stats.strip()
      if stats_str.startswith('['):                           # Podman: normalize array to one-object-per-line
        stats_str = '\n'.join(
          json.dumps({**item, 'Name': item.get('name', item.get('Name','')), 'MemUsage': item.get('mem_usage', item.get('MemUsage',''))})
          for item in json.loads(stats_str))

      for line in stats_str.split('\n'):
        if not line.startswith('{'):
          continue
        docker_stats = json.loads(line)
        c_name = docker_stats.get('Name', None)
        if c_name not in stat_box:                          # Ignore containers not in this lab
          continue
        mem_str = docker_stats.get('MemUsage', '').split('/')[0].strip()
        mem_kb = strings.parse_memory_size(mem_str)
        stat_box[c_name].memory = strings.format_memory_size(mem_kb) if mem_kb else mem_str
    except Exception as ex:
      log.print_verbose(f'Cannot get Docker memory usage: {ex}')

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
    
    utils.validate_docker_image(node,topology,self.image_cache)

  def deploy_node_config(self, node: Box, topology: Box, deploy_list: list) -> None:
    cfg_files = node.get('clab.config_templates',[])
    if not cfg_files:                                          # No node files => no config to deploy here
      return
    node_name = self.get_node_name(node.name,topology)          # ... get container/namespace name
    configs.deploy_container_config(node,node_name,deploy_list)

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
