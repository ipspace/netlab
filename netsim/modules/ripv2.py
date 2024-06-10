#
# RIPv2/RIPng transformation module
#
import typing

from box import Box

from . import _Module,_routing
from . import bfd
from ..utils import log
from ..augment import devices

class RIPv2(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)

    _routing.router_id(node,'ripv2',topology.pools)
    
    bfd.bfd_link_state(node,'ripv2')

    #
    # Cleanup routing protocol from external/disabled interfaces
    for intf in node.get('interfaces',[]):
      if not _routing.external(intf,'ripv2'):                   # Remove external interfaces from RIPv2 process
        _routing.passive(intf,'ripv2',topology,features,node)   # Set passive flag on other RIPv2 interfaces

    #
    # Final steps:
    # * move RIP-enabled VRF interfaces into VRF dictionary
    # * Calculate address families
    # * Remove RIPv2 module if there are no RIPv2-enabled global or VRF interfaces
    #
    _routing.remove_unaddressed_intf(node,'ripv2')
    _routing.build_vrf_interface_list(node,'ripv2',topology)
    _routing.routing_af(node,'ripv2',features)
    _routing.remove_vrf_routing_blocks(node,'ripv2')
    _routing.remove_unused_igp(node,'ripv2',topology.defaults.get('ripv2.warnings.inactive',False))
    if 'ripv2' in node and 'loopback' in node:
      node.loopback.ripv2.passive = False

    _routing.check_vrf_protocol_support(node,'ripv2','ipv4','ripv2',topology)
    _routing.check_vrf_protocol_support(node,'ripv2','ipv6','ripng',topology)
