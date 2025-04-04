#
# Bird quirks
#
from box import Box

from . import _Quirks, report_quirk
from ._common import check_indirect_static_routes

"""
set_unnumbered_peers - check for ipv4 unnumbered interfaces with a single direct peer
"""
def set_unnumbered_peers(node: Box, topology: Box) -> None:
  err_data = []
  for intf in node.get('interfaces',[]):
    if intf.get('ipv4',None) is True and '_parent_intf' in intf:
      if len(intf.neighbors)==1:
        peer = topology.nodes[ intf.neighbors[0].node ]
        if 'ipv4' in peer.loopback:
          intf._bird_unnumbered_peer = peer.loopback.ipv4
          continue
      err_data.append(f'Unnumbered interface without direct IPv4 peer {intf.ifname}')
  
  if err_data:
    report_quirk(
      f'node {node.name} has unsupported unnumbered interface(s)',
      quirk='no_unnumbered_peer',
      more_data=err_data,
      node=node)

class Bird(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    set_unnumbered_peers(node,topology)
    check_indirect_static_routes(node)
