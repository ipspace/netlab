#
# Cisco ASA quirks
#
from box import Box

from . import _Quirks
from ..utils import log

def check_isis_p2p_interfaces(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if not 'isis' in intf:
      continue
    for neighbor in intf.neighbors:
      remote_node = neighbor.node
      remote_interfaces = topology.nodes[remote_node].interfaces
      for rintf in remote_interfaces:
        if rintf.ifname == neighbor.ifname:
          if intf.get('isis.network_type',None) == "point-to-point":
            log.error(
              f'Cisco ASA does not support P2P IS-IS links.'
              f'Problematic Interface: {remote_node} {neighbor.ifname}',
              log.IncorrectType,
              'quirks',
            )

class ASA(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module', [])
    if 'isis' in mods:
      check_isis_p2p_interfaces(node, topology)
