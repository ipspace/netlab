#
# IS-IS transformation module
#
from box import Box

from . import _Module, _routing


class EIGRP(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    _routing.router_id(node,'eigrp',topology.pools)
    for intf in node.get('interfaces',[]):
      if not _routing.external(intf,'eigrp'):
        _routing.passive(intf,'eigrp',topology)

    _routing.igp_post_transform(node,topology,proto='eigrp',vrf_aware=False)
