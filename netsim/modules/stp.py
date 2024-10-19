#
# STP transformation module
#
from box import Box

from ..augment import devices
from ..utils import log

from . import _Module

class STP(_Module):

  # Check for device support when pvrst is required
  def node_pre_transform(self, node: Box, topology: Box) -> None:

    if not topology.stp.get('pvrst',False):
      return

    if not 'stp' in node.get('module',[]):
      return
    
    features = devices.get_device_features(node,topology.defaults)

    if not 'stp' in features:
      log.error(
        f'node {node.name} (device {node.device}) does not support STP module',
        log.IncorrectValue,
        'stp')
      return

    if not features.stp.get('pvrst',False):
      log.error(
        f'node {node.name} (device {node.device}) does not support per-VLAN STP (PVRST)',
        log.IncorrectValue,
        'stp')
