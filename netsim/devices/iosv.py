#
# Cisco IOSv quirks
#
from box import Box

from . import _Quirks,report_quirk
from ..utils import log
from ..modules import _routing

# Cisco IOSv does not support VRRP on BVI interfaces. Go figure...
#
def check_vrrp_bvi(node: Box, topology: Box) -> None:
  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'vrrp':                     # No VRRP, move on
      continue

    if intf.get('type',None) != 'svi':                                  # Not a BVI interface, move on
      continue

    log.error(
      f'Cisco IOSv cannot run VRRP on BVI interfaces.',
      log.IncorrectType,
      'quirks')
    return

def check_ripng_passive(node: Box, topology: Box) -> None:
  for intf in _routing.routing_protocol_interfaces(node,'ripv2'):
    if 'ipv6' in intf and intf.get('ripv2.passive',False):
      report_quirk(
        f'Cisco IOS/IOS-XE does not support passive RIPng interfaces - node {node.name} intf {intf.ifname}({intf.name})',
        node,
        quirk='ripng.passive',
        category=Warning)

def common_ios_quirks(node: Box, topology: Box) -> None:
  mods = node.get('module',[])
  if 'ospf' in mods:
    _routing.get_unique_router_ids(node,'ospf',topology)

  if 'ripv2' in mods:
    check_ripng_passive(node,topology)

class IOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    if 'gateway' in mods:
      check_vrrp_bvi(node,topology)

    common_ios_quirks(node,topology)
