#
# Containerlab provider module
#
import typing

from box import Box

from ...augment import devices
from ...cli import external_commands
from ...data import append_to_list
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
