#
# IS-IS transformation module
#
from box import Box

from . import _Module,_routing

class EIGRP(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    _routing.router_id(node,'eigrp',topology.pools)
    for intf in node.get('interfaces',[]):
      if not _routing.external(intf,'eigrp'):
        _routing.passive(intf,'eigrp',topology)

    _routing.remove_unaddressed_intf(node,'eigrp')
    _routing.remove_vrf_interfaces(node,'eigrp')
    _routing.routing_af(node,'eigrp')
