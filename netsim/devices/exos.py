from box import Box

from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk


def check_vrrp_address_families(node: Box) -> None:
  for intf in node.interfaces:
    if intf.get('gateway.protocol',None) != 'vrrp':
      continue

    if 'ipv4' in intf.gateway and 'ipv6' in intf.gateway:
      report_quirk(
        text=f'Extreme EXOS cannot configure IPv4 and IPv6 virtual addresses in the same VRRP instance ({node.name} {intf.ifname})',
        node=node,
        quirk='vrrp_mixed_af',
        category=log.IncorrectType)
      return


class EXOS(_Quirks):

  @classmethod
  def device_quirks(cls, node: Box, topology: Box) -> None:
    if 'gateway' in node.get('module',[]):
      check_vrrp_address_families(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'community.network',version='5.1.0')
