#
# STP transformation module
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Module

"""
supports_stp - checks whether the given interface supports STP settings
"""
def supports_stp(intf: Box) -> bool:
  if 'ipv4' in intf or 'ipv6' in intf:                                       # Skip IP interfaces
    return False
  if 'virtual_interface' in intf:                                            # Skip virtual interfaces
    return False
  return True


"""
configure_stub_port_type - for a L2 interface where all devices connected are hosts, sets the stp.port_type as <stub_port_type>
"""
def configure_stub_port_type(intf: Box, stub_port_type: str, topology: Box) -> bool:
  if not (intf.get('neighbors',[]) or intf.get('_vlan_saved_neighbors',[])): # Skip interfaces with no neighbors
    return False
  for n in intf.get('neighbors',intf.get('_vlan_saved_neighbors')):
    neighbor = topology.nodes[n.node]
    if neighbor.get('role',None) != 'host':
      return False
  intf.stp.port_type = stub_port_type                                        # All neighbors are hosts
  return True

class STP(_Module):

  # Check stp.supported_protocols, stp.priority, stp.port_priority, per VLAN support and stp.enable_per_port
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not node.get('stp.enable', True):   # if STP is disabled, don't complain about feature support
      return
    features = devices.get_device_features(node,topology.defaults)

    supported_protocols = features.get("stp.supported_protocols",[])
    if node.stp.protocol not in supported_protocols:
      log.error(
        f'node {node.name} (device {node.device}) does not support requested STP protocol ({node.stp.protocol})',
        log.IncorrectValue,
        'stp')

    priority = node.get('stp.priority',None)
    if priority is not None and (priority % 4096):
        log.error(
            f'node {node.name} (device {node.device}) stp.priority: {priority} must be a multiple of 4096',
            log.IncorrectValue,
            'stp')

    stub_port_type = topology.get('stp.stub_port_type','none')
    for intf in node.get('interfaces',[]):
      if 'stp' in intf:
        if 'ipv4' in intf or 'ipv6' in intf:
          log.error(
            f'node {node.name}: Cannot apply STP to L3 interface ({intf.name})',
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
      if not features.get('stp.port_type',False):                   # If the device doesn't support it, move on
        continue
      stp_port_type = intf.get('stp.port_type',None)
      if stp_port_type is None and supports_stp(intf):
        if stub_port_type != 'none':
          if configure_stub_port_type(intf,stub_port_type,topology):
            continue
        if 'vlan' in intf:
          if 'access' in intf.vlan:
            vlan = node.get(f'vlans.{intf.vlan.access}')
            stp_port_type = vlan.get('stp.port_type',None)
            if stp_port_type is not None:
              intf.stp.port_type = stp_port_type
              continue
        stp_port_type = node.get('stp.port_type',None)              # Apply node level setting to ports that support it
        if stp_port_type is not None:
          intf.stp.port_type = stp_port_type                        # Conditional copy
      
    # Check if per-VLAN priority is being used
    for vname,vdata in node.get('vlans',{}).items():
      if vdata.get('stp.priority',None):
        if node.stp.protocol != 'pvrst':
          log.error(
            f"Topology requires per-VLAN STP (pvrst) used on VLAN '{vname}' but global default is '{node.stp.protocol}'",
            log.IncorrectValue,
            'stp')
        elif not 'pvrst' in features.get('stp.supported_protocols',[]):
          log.error(
            f"node {node.name} (device {node.device}) does not support per-VLAN STP (pvrst) used on VLAN '{vname}'",
            log.IncorrectValue,
            'stp')

    # Normalize STP data model: mark interfaces that need STP configuration
    # This makes templates easier to consume by avoiding complex Jinja2 filters like:
    #   ifdata.vlan.trunk|default({})|dict2items|map(attribute='value')|selectattr('stp','defined')
    #
    # An interface needs STP config if it has:
    #   - Direct STP settings (ifdata.stp), OR
    #   - STP configuration in any trunk VLAN (ifdata.vlan.trunk[vname].stp)
    #
    # Templates can now simply check: ifdata._has_stp_config|default(False)
    # This applies to all devices, not just NVUE/OS10, making the data model consistent
    for intf in node.get('interfaces',[]):
      # Check for direct STP configuration
      if 'stp' in intf:
        intf._has_stp_config = True
        continue

      # Check for STP configuration in trunk VLANs
      trunk = intf.get('vlan.trunk',{})
      if trunk and any('stp' in vdata for vdata in trunk.values()):
        intf._has_stp_config = True
