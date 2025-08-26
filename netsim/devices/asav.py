#
# Cisco ASA quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


def check_isis_p2p_interfaces(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if not 'isis' in intf:
      continue
    if intf.get('isis.network_type',None) != "point-to-point":
      continue

    for neighbor in intf.neighbors:
      report_quirk(
        text=f'Cisco ASA does not support P2P IS-IS links',
        node=node,
        more_data=[ f'Node {node.name} {intf.ifname} connected to {neighbor.node} {neighbor.ifname}' ],
        category=log.IncorrectType)

class ASA(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module', [])
    if 'isis' in mods:
      check_isis_p2p_interfaces(node, topology)
