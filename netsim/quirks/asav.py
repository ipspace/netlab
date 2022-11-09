#
# Cisco ASA quirks
#
from box import Box

from . import _Quirks
from .. import common
from ..data import get_from_box

def check_isis_p2p_interfaces(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    for neighbor in intf['neighbors']:
      remote_node = get_from_box(neighbor, 'node')
      remote_interface_name = get_from_box(neighbor, 'ifname')
      remote_interfaces = topology[f'nodes.{remote_node}.interfaces']
      for rintf in remote_interfaces:
        if get_from_box(rintf, 'ifname') == remote_interface_name:
          if get_from_box(rintf, 'isis.network_type') != None:
            common.error(
                f'Cisco ASA does not support P2P IS-IS links.'
                f'Problematic Interface: {remote_node} {remote_interface_name}',
                common.IncorrectType,
                'quirks',
            )

class ASA(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module', [])
    if 'isis' in mods:
      check_isis_p2p_interfaces(node, topology)
