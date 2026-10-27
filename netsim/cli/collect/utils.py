#
# Configuration collection utility functions
#

import os
import pathlib
import typing

from box import Box

from ...augment import devices as a_devices
from ...utils import log
from .. import error_and_exit, fs_cleanup


def collectable(nodeset: list, topology: Box) -> typing.Tuple[list,list]:
  """
  Return a list of devices from which the configuration can be collected. Generate
  warning for unsupported devices and exit if no feasible nodes are found.
  """
  n_miss: list = []
  n_list: list = []
  d_miss: set = set()
  defaults = topology.defaults

  for n in nodeset:
    ndata = topology.nodes[n]
    features = a_devices.get_device_features(ndata,defaults)
    if not features.get('initial.collect',False):
      d_miss.add(ndata.device)
      n_miss.append(n)
    else:
      n_list.append(n)

  if n_miss:
    log.warning(
      text='Cannot collect information from device(s) '+','.join(sorted(d_miss)),
      module='collect',
      more_data='Node(s): '+','.join(n_miss))

  if not n_list:
    error_and_exit('Cannot collect information from any of the specified node(s), exiting')

  return (n_list,n_miss)

def create_output(path: str) -> None:
  """
  Cleans up and recreates the configuration collection directory
  """

  fs_cleanup([ path ])
  try:
    os.mkdir(path)
  except Exception as ex:
    log.fatal(f"Cannot create output directory {path}: {ex}")

  if not log.QUIET:
    log.info(f"Collecting configs into {str(pathlib.Path(path).absolute())}")
