#
# Arista EOS quirks
#
from box import Box

from . import _Quirks
from ..utils import log
from ..augment import devices

def check_ospf_vrf_default(node: Box) -> None:
  for vname,vdata in node.get('vrfs',{}).items():
    if vdata.get('ospf.default',None):
      log.error(
        f"VRF OSPF default route is not working on Cumulus Linux (node {node.name}, vrf {vname})",
        category=log.IncorrectType,
        module='quirks')

class Cumulus(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'ospf' in mods and 'vrfs' in node:
      check_ospf_vrf_default(node)
