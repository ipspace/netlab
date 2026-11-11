#
# Collect device configuration(s) with netmiko
#

import typing

from box import Box

from ...augment import devices as a_devices
from ...utils import log, netmiko
from . import utils as c_utils


def collect(node: str, output: str, suffix: str, topology: Box) -> typing.Optional[bool]:
  """
  Try to collect device configuration with netmiko. Return None on errors or
  if the device does not support netmiko-based config collection
  """
  if netmiko.NETMIKO_IS_MISSING:                  # Don't even try if netmiko is not installed
    return None
  n_data = topology.nodes[node]
  features = a_devices.get_device_features(n_data,topology.defaults)
  nm_collect = features.get('netmiko.collect',None)
  if not nm_collect:                              # No netmiko-based config collection?
    return None                                   # ... move on

  try:
    params = netmiko.prepare_params(n_data,topology)
    if not params:                                # Cannot get netmiko parameters?
      return None                                 # ... move on
    session = netmiko.connect(n_data,params)
    if not session:                               # Cannot open an SSH session?
      return False                                # ... report an error
    for action,cmd in nm_collect.items():         # Collect all requested configs
      if action.startswith('_'):                  # ... elements starting with underscore are cleanup parameters
        continue
      stdout = session.send_command(cmd)          # Send the collection command
      if not stdout:                              # ... nothing collected? Move on
        continue
      if not isinstance(stdout,str):              # If we got back anything but a string, we have no idea what to do
        return None

      stdout = c_utils.cleanup(stdout,action,nm_collect)
      c_utils.save_config(                        # ... and save the collected string
        filename=node + suffix if action == 'config' else f'{node}-{action}',
        directory=output,
        contents=stdout)

    return True

  except Exception as ex:
    log.error(f'Failed to collect device configuration from {node}: {ex}')
    return False
