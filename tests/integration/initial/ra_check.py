#
# Check whether the device under test supports VRFs and removes
# VRF links and related tests if needed
#

from box import Box

from netsim.augment.devices import get_device_features
from netsim.utils import log


def pre_transform(topology: Box) -> None:
  for _,ndata in topology.nodes.items():
    if ndata.get('role',None) != 'router':
      continue

    features = get_device_features(ndata,topology.defaults)
    if features.get('initial.ra',None):
      continue

    log.error(
      text=f'Device {ndata.device}/{ndata.name} does not support configurable IPv6 router advertisements',
      category=log.IncorrectType,
      module='ra_check')
