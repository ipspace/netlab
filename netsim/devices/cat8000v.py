#
# Cisco IOS-XE quirks
#
from box import Box

from ..utils import log
from . import report_quirk
from .iol import IOSXE as _IOSXE
from .iosv import use_paramiko
from .iosvl2 import check_reserved_vlans


def check_premier_license(node: Box) -> None:
  if node.get('cat8000v.license',None) == 'premier':
    return
  
  mod_list = node.get('module',[])
  for lic_mod in ['mpls','sr-mpls','srv6','vxlan','evpn']:
    if lic_mod in mod_list:
      report_quirk(
        f'Node {node.name} needs "network-premier" license to run {lic_mod}',
        node=node,
        more_hints=['See https://netlab.tools/caveats/#cisco-catalyst-8000v for more details'],
        quirk='license',
        category=log.MissingDependency)

class C8KV(_IOSXE):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)
    check_reserved_vlans(node,topology)
    check_premier_license(node)
    use_paramiko(node,topology)
