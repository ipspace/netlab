#
# Containerlab provider module
#
import json
import typing

from box import Box

from ...augment import devices
from ...cli import external_commands
from ...data import append_to_list, types
from ...utils import log


def list_bridges( topology: Box ) -> typing.Set[str]:
  '''
  list_bridges: return a set of all internal bridges clab would have to create. This
  function is not used if clab is not a primary provider and skips all bridges that
  the customer previously created.
  '''
  return { l.bridge for l in topology.links if l.bridge and l.node_count > 2 and not 'external_bridge' in l.clab }

def add_clab_exec(node: Box, gvar: str, topology: Box) -> None:
  '''
  add_clab_exec: Add commands from the specified group variable (for example,
  'netlab_config_exec' or 'netlab_start_exec') to the clab.exec list.

  These commands can be used to delay container start when using Linux configuration
  scripts ('netlab_config_mode' via 'netlab_config_exec') or to introduce additional
  startup delay when containerlab itself does not handle that ('netlab_start_exec').
  '''
  cfg_exec = devices.get_node_group_var(node,gvar,topology.defaults) or []
  if cfg_exec:
    append_to_list(node,'clab.exec',cfg_exec,flatten=True)

def get_linux_ifname(netns: str, intf: str) -> str:
  '''
  Get the actual Linux interface name inside the specified network namespace,
  based on the interface name provided.
  '''
  out = external_commands.run_command(
    cmd=f'{netns} ip -j link show dev {intf}',
    ignore_errors=True,return_stdout=True,check_result=True)
  if not isinstance(out,str):
    return intf
  try:
    data = json.loads(out)
    return data[0].get('ifname',intf) if data else intf
  except Exception:
    return intf

def validate_docker_image(node: Box,topology: Box,image_cache: dict) -> None:
    docker_image = external_commands.run_command(           # Get image status from Docker
                      ['docker', 'image', 'ls', '--format', 'json', node.box],
                      check_result=True, ignore_errors=True, return_stdout=True)
    image_cache[node.box] = docker_image

    if docker_image:                                        # If we got something back, the image is installed
      return
    
    log.print_verbose(f'clab: image {node.box} is not installed: {docker_image}')
    dp_data = devices.get_provider_data(node,topology.defaults)
    if 'build' not in dp_data:                              # We have no build recipe, let's hope it's downloadable
      log.info(f"We'll try to download Docker image {node.box} used by {node.name}",module='clab')
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

def create_clab_batches(topology: Box) -> None:
  """
  Create batches of containers to deal with very large topologies. The batches
  are implemented with the containerlab stages.wait_for attribute which is
  derived from the start_after list
  """
  clab_defaults = topology.defaults.providers.clab
  if not clab_defaults.get('batch_size',None):
    return

  types.must_be_int(clab_defaults,'batch_size','defaults.providers.clab',module='clab',min_value=1,max_value=50)
  log.exit_on_error()

  batch_size = clab_defaults.batch_size
  node_list = [ n_name for (n_name,n_data) in topology.nodes.items()
                  if devices.get_provider(n_data,topology.defaults) == 'clab'
                     and not n_data.get('unmanaged',False) ]

  while True:
    prev_batch = node_list[:batch_size]
    node_list = node_list[batch_size:]
    if not node_list:
      break
    for n in node_list[:batch_size]:
      ndata = topology.nodes[n]
      append_to_list(ndata,'clab.start_after',prev_batch,flatten=True)


def create_clab_stages(topology: Box) -> None:
  """
  Create containerlab stages dictionary from clab.start_after attribute
  """
  defaults = topology.defaults
  wf_method_cache: dict = {}
  for ndata in topology.nodes.values():
    if devices.get_provider(ndata,defaults) != 'clab':
      continue
    wf_list = ndata.get('clab.start_after',[])
    if not wf_list:
      continue
    p_waitfor = [ wf.node for wf in ndata.clab.get('stages.create.wait-for',[]) ]
    for wf_node in wf_list:
      if wf_node in p_waitfor:
        continue
      wf_ndata = topology.nodes[wf_node]
      if devices.get_provider(wf_ndata,defaults) != 'clab':
        log.error(
          f'Container {ndata.name} cannot wait for a non-container node {wf_node}',
          category=log.IncorrectValue,
          module='clab')
      if wf_node in wf_method_cache:
        wf_method = wf_method_cache[wf_node]
      else:
        features = devices.get_device_features(wf_ndata,defaults)
        wf_method = 'healthy' if features.get('initial.healthcheck') else 'configure'
        wf_method_cache[wf_node] = wf_method
      append_to_list(ndata.clab.stages.create,'wait-for',{ 'node': wf_node, 'stage': wf_method })
