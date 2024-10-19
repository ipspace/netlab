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

  # Check max port_priority values
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not 'stp' in node.get('module',[]):
      return
    features = devices.get_device_features(node,topology.defaults)

    priority = node.get('stp.priority',0)
    if priority and (priority % 4096):
        log.error(
            f'node {node.name} (device {node.device}) stp.priority: {priority} must be a multiple of 4096',
            log.IncorrectValue,
            'stp')

    port_priority = features.get('stp.port_priority', { 'max': 255 } )
    for intf in node.get('interfaces',[]):
      if 'stp' in intf:
        val = intf.get('stp.port_priority',0)
        if val > port_priority.max:
          log.error(
            f'node {node.name} (device {node.device}) only supports stp.port_priority up to {port_priority.max}, found {val}',
            log.IncorrectValue,
            'stp')
        elif 'multiple' in port_priority and (val % port_priority.multiple):
          log.error(
            f'node {node.name} (device {node.device}) stp.port_priority {val} must be a multiple of {port_priority.multiple}',
            log.IncorrectValue,
            'stp')
