#
# Mikrotik RouterOS7 quirks
#
from box import Box

from ..utils import log
from . import _common, _Quirks, report_quirk


def check_vpnv6_af(node: Box, topology: Box) -> None:
  for ngb in node.get('bgp.neighbors',[]):
    if 'vpnv6' in ngb:
      report_quirk(
        f'We could not get VPNv6 AF to work on Mikrotik RouterOS7 (node {node.name})',
        node=node,
        quirk='vpnv6',
        category=log.IncorrectValue,
        module='quirks')
      return

class RouterOS7(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if node.get('mpls.vpn',False):
      check_vpnv6_af(node,topology)
    _common.check_tagged_vlan_1(node)
