#
# Cisco ASA quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


def check_isis_p2p_interfaces(node: Box, topology: Box, igp: str = 'isis') -> None:
  for intf in node.interfaces:
    if not igp in intf:
      continue
    if intf[igp].get('network_type',None) != "point-to-point":
      continue

    report_quirk(
      text=f'Cisco ASA does not support P2P {igp} links',
      node=node,
      more_data=[ f'Node {node.name} {intf.ifname} ({intf.name})' ],
      category=log.IncorrectType)

class ASA(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module', [])
    for igp in ('isis','ospf'):
      if igp in mods:
        check_isis_p2p_interfaces(node, topology,igp=igp)

    if node.get('ospf.af.ipv6',False):
      report_quirk(
        text=f"netlab cannot configure OSPFv3 on ASAv node '{node.name}'",
        node=node,
        category=log.IncorrectType)
