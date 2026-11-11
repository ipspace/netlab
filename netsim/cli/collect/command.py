#
# Collect device configuration(s) with netmiko
#

import typing
from argparse import Namespace

from box import Box

from ...augment import devices as a_devices
from ...utils import log
from .. import connect
from . import utils as c_utils


def collect(node: str, output: str, suffix: str, topology: Box) -> typing.Optional[bool]:
  """
  Try to collect device configuration with "netlab collect" commands. Return None on errors or
  if the device does not support command-based config collection
  """
  n_data = topology.nodes[node]
  features = a_devices.get_device_features(n_data,topology.defaults)
  nm_collect = features.get('command.collect',None)
  if not nm_collect:                              # No netmiko-based config collection?
    return None                                   # ... move on

  try:
    for action,cmd in nm_collect.items():         # Collect all requested configs
      if action.startswith('_'):                  # ... elements starting with underscore are cleanup parameters
        continue

      result = connect.connect_to_node(
                  node=node,
                  args=Namespace(quiet=True,output=True,show=None,verbose=False,stdout=True),
                  rest=[cmd],
                  topology=topology,
                  log_level=connect.LogLevel.NONE)
      if result is False:                         # Command failed?
        log.error(
          f'Failed to collect {action} configuration from {node}',
          skip_header=True,
          module='collect',
          category=log.ErrorAbort,
          more_hints=f"Command: {cmd}")
        return None
      if not result:                              # ... nothing collected? Move on
        log.info(f'{action} configuration on {node} is empty; skipping')
        continue
      if not isinstance(result,str):              # If we got back anything but a string, we have no idea what to do
        return None

      stdout = c_utils.cleanup(result,action,nm_collect)
      c_utils.save_config(                        # ... and save the collected string
        filename=node + suffix if action == 'config' else f'{node}-{action}',
        directory=output,
        contents=stdout)

    return True

  except Exception as ex:
    log.error(f'Failed to collect device configuration from {node}: {ex}',skip_header=True)
    return False
