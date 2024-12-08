#
# STP transformation module
#
from box import Box

from ..augment import devices
from ..utils import log

from . import _Module

"""
configure_stub_port_type - for a L2 interface where all devices connected are hosts, sets the stp.port_type as <stub_port_type>
"""
def configure_stub_port_type(intf: Box, stub_port_type: str, topology: Box) -> None:
  if not (intf.get('neighbors',[]) or intf.get('_vlan_saved_neighbors',[])): # Skip interfaces with no neighbors
    return
  if 'ipv4' in intf or 'ipv6' in intf:                                       # Skip IP interfaces
    return
  if 'virtual_interface' in intf:                                            # Skip virtual interfaces
    return
  for n in intf.get('neighbors',intf.get('_vlan_saved_neighbors')):
    neighbor = topology.nodes[n.node]
    if neighbor.get('role',None) != 'host':
      return
  intf.stp.port_type = stub_port_type                                        # All neighbors are hosts

class STP(_Module):

  # Check stp.supported_protocols, stp.priority, stp.port_priority, per VLAN support and stp.enable_per_port
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not node.get("stp.enable", True):   # if STP is disabled, don't complain about feature support
      return
    features = devices.get_device_features(node,topology.defaults)

    protocol = topology.get("stp.protocol","stp")
    supported_protocols = features.get("stp.supported_protocols",[])
    if protocol not in supported_protocols:
      log.error(
        f'node {node.name} (device {node.device}) does not support requested STP protocol ({protocol})',
        log.IncorrectValue,
        'stp')

    priority = node.get('stp.priority',0)
    if priority and (priority % 4096):
        log.error(
            f'node {node.name} (device {node.device}) stp.priority: {priority} must be a multiple of 4096',
            log.IncorrectValue,
            'stp')

    stub_port_type = topology.get('stp.stub_port_type','edge') if features.get('stp.port_type',False) else 'none'
    for intf in node.get('interfaces',[]):
      if 'stp' in intf:
        if 'ipv4' in intf or 'ipv6' in intf:
          log.error(
            f'node {node.name}: Cannot apply STP to L3 interface ({intf.ifname})',
            log.IncorrectAttr,
            'stp')
        if 'enable' in intf.stp and not features.get('stp.enable_per_port',False):
          log.error(
            f'node {node.name} (device {node.device}) does not support enabling/disabling STP only on a specific port ({intf.ifname})',
            log.IncorrectValue,
            'stp')
        if 'port_type' in intf.stp and not features.get('stp.port_type',False):
          log.error(
            f'node {node.name} (device {node.device}) does not support configuration of STP port_type on ({intf.ifname})',
            log.IncorrectValue,
            'stp')
      if stub_port_type != 'none' and not intf.get('stp.port_type',None):
        configure_stub_port_type(intf,stub_port_type,topology)
      
    # Check if per-VLAN priority is being used
    for vname,vdata in node.get('vlans',{}).items():
      if vdata.get('stp.priority',None):
        stp_proto = topology.get('stp.protocol','stp')
        if stp_proto != 'pvrst':
          log.error(
            f"Topology requires per-VLAN STP (pvrst) used on VLAN '{vname}' but global default is '{stp_proto}'",
            log.IncorrectValue,
            'stp')
        elif not 'pvrst' in features.get('stp.supported_protocols',[]):
          log.error(
            f"node {node.name} (device {node.device}) does not support per-VLAN STP (pvrst) used on VLAN '{vname}'",
            log.IncorrectValue,
            'stp')
