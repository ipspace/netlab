#
# OpenBSD quirks
#
from box import Box

from . import _Quirks,report_quirk
from ._common import check_indirect_static_routes
from ..utils import log

"""
You cannot reach OpenBSD loopback interface unless it runs as a router (with IP forwarding)
This quirk changes the node 'mode' if the node has a loopback interface.
"""
def check_loopback(node: Box, topology: Box) -> None:
  if not node.get('loopback',None):
    return

  if node.get('role','host') == 'host':
    node.role = 'router'
    report_quirk(
      f'node {node.name} has a loopback interface. Changing node role to router',
      quirk='role_router',
      category=Warning,
      node=node)

class OpenBSD(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_loopback(node,topology)
    check_indirect_static_routes(node)
