#
# Arista EOS quirks
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Quirks, report_quirk


def check_ospf_vrf_default(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if vdata.get('ospf.default',None):
      report_quirk(
        text=f"VRF OSPF default route is not working (node {node.name}, vrf {vname})",
        node=node,
        quirk='ospf_default',
        category=log.IncorrectType)

class Cumulus(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if devices.get_provider(node,topology) == 'clab':
      report_quirk(
        text=f"We do not test Cumulus containers ({node.name}). They might not work correctly",
        node=node,
        category=Warning,
        quirk="unsupported_container",
        more_hints=[ "See https://netlab.tools/caveats/#caveats-cumulus for more details "])

    mods = node.get('module',[])
    if 'ospf' in mods and 'vrfs' in node:
      check_ospf_vrf_default(node)
