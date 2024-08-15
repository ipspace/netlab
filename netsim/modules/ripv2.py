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

    _routing.igp_post_transform(node,topology,proto='ripv2',vrf_aware=True)
    _routing.check_vrf_protocol_support(node,'ripv2','ipv4','ripv2',topology)
    _routing.check_vrf_protocol_support(node,'ripv2','ipv6','ripng',topology)
    if 'ripv2' in node and 'loopback' in node:
      node.loopback.ripv2.passive = False
