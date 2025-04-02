#
# Linux quirks
#
from box import Box

from . import _Quirks,report_quirk
from ._common import check_indirect_static_routes
from ..utils import log
from ..augment import devices

def check_clab_modules(node: Box, topology: Box) -> None:
  if 'dhcp' in node.get('module',[]):
    report_quirk(
      text=f"netlab does not support DHCP functionality in Linux containers (node {node.name})",
      node=node,
      more_hints=[ "Use 'cumulus' for DHCP client or 'dnsmasq' for DHCP server" ],
      category=log.IncorrectType,
      quirk='clab_dhcp_client')

def check_vm_modules(node: Box, topology: Box) -> None:
  if 'vlan' in node.get('module',[]):
    report_quirk(
      text=f"netlab does not support VLANs in Linux virtual machines (node {node.name})",
      node=node,
      more_hints=[ "Use 'frr' device instead" ],
      category=log.IncorrectType,
      quirk='vm_vlan')

class Linux(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)

    if devices.get_provider(node,topology) == 'clab':
      check_clab_modules(node,topology)
    else:
      check_vm_modules(node,topology)
