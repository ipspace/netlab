#
# STP transformation module
#
from box import Box

from ..augment import devices
from ..utils import log

from . import _Module

class STP(_Module):

  # Check for device support for globally selected STP protocol variant
  def node_pre_transform(self, node: Box, topology: Box) -> None:

    protocol = topology.get("stp.protocol","stp")
    features = devices.get_device_features(node,topology.defaults)

    supported_protocols = features.get("stp.supported_protocols",[])
    if protocol not in supported_protocols:
      log.error(
        f'node {node.name} (device {node.device}) does not support requested STP protocol ({protocol})',
        log.IncorrectValue,
        'stp')

  # Check max port_priority values
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not node.get("stp.enable", True):
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
        
        # Check if per-VLAN priority is being used
        if intf.type=='svi' and 'priority' in intf.stp:
          stp_proto = topology.get('stp.protocol','stp')
          if stp_proto != 'mstp':
            log.error(
              f'Topology requires per-VLAN STP (MSTP) used on VLAN {intf.name} but global default is {stp_proto}',
              log.IncorrectValue,
              'stp')
          elif not 'mstp' in features.get('stp.supported_protocols',[]):
            log.error(
              f'node {node.name} (device {node.device}) does not support per-VLAN STP (MSTP) used on VLAN {intf.name}',
              log.IncorrectValue,
              'stp')
