#
# Collect device configuration(s) with netmiko
#

import re
import typing

from box import Box

from ...augment import devices as a_devices
from ...utils import log, netmiko
from . import utils as c_utils


def cleanup(contents: str, action: str, collect: Box) -> str:
  """
  Clean the contents gathered with 'action' command
  """
  lines = contents.split('\n')
  skip = collect.get(f'_{action}_skip',None)      # Do we have to skip a few lines?
  if skip:
    lines = lines[skip:]

  clean = collect.get(f'_{action}_clean',None)    # RE-based cleanup?
  if clean:
    cl_re = re.compile(clean)                     # Filter config lines with the specified RE  
    lines = [ line for line in lines if not cl_re.search(line) ]

  return '\n'.join(lines)                         # Finally, convert lines back to config string

def collect(node: str, output: str, suffix: str, topology: Box) -> typing.Optional[bool]:
  """
  Try to collect device configuration with netmiko. Return None on errors or
  if the device does not support netmiko-based config collection
  """
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

      stdout = cleanup(stdout,action,nm_collect)
      c_utils.save_config(                        # ... and save the collected string
        filename=node + suffix if action == 'config' else f'{node}-{action}',
        directory=output,
        contents=stdout)

    return True

  except Exception as ex:
    log.error(f'Failed to collect device configuration from {node}: {ex}')
    return False
