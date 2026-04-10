#
# VyOS quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk


def check_aspath_prepend(node: Box, topology: Box) -> None:
  for pname,plist in node.get('routing.policy',{}).items():
    for pentry in plist:
      if ' ' not in pentry.get('set.prepend.path',''):
        continue
      report_quirk(
        text=f"cannot prepend more than a single AS to the AS path (node {node.name} policy {pname})",
        node=node,
        category=log.IncorrectValue,
        quirk='aspath_prepend')

class Vyos(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if 'routing' in node.get('module',[]):
      check_aspath_prepend(node,topology)
