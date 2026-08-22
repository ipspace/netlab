#
# Linux quirks
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Quirks, report_quirk
from ._common import check_indirect_static_routes


def check_vm_modules(node: Box, topology: Box) -> None:
  if 'vlan' in node.get('module',[]):
    report_quirk(
      text=f"netlab does not support VLANs in Linux virtual machines (node {node.name})",
      node=node,
      more_hints=[ "Use 'frr' device instead" ],
      category=log.IncorrectType,
      quirk='vm_vlan')

def check_extra_loopbacks(node: Box, topology: Box) -> None:
  intf_list = [ intf.ifname for intf in node.get('interfaces',[]) if intf.type == 'loopback' ]
  if not intf_list:
    return

  report_quirk(
    text=f"Cannot use additional loopbacks ({' '.join(intf_list)}) on node {node.name}",
    more_hints=[ f"netplan (used by Ubuntu Linux VMs) cannot create dummy interfaces" ],
    node=node,
    category=log.IncorrectType,
    quirk='ubuntu_dummy')

def etc_resolv_mapping(node: Box, topology: Box) -> None:
  """
  Add /etc/resolv.conf mapping for Linux-based containers using DNS services
  """
  if devices.get_provider(node,topology) != 'clab':
    return
  if 'services.dns._server_list' not in node:
    return
  if 'clab.node.config_templates.resolv' not in node:
    node.clab.config_templates.resolv = '/etc/resolv.conf'

class Linux(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    etc_resolv_mapping(node,topology)

    if devices.get_provider(node,topology) != 'clab':
      check_vm_modules(node,topology)
      check_extra_loopbacks(node,topology)
