#
# Dell OS10 quirks
#
from box import Box

from . import _Quirks,need_ansible_collection,report_quirk
from ..utils import log
from ..augment import devices

def check_vlan_ospf(node: Box, vname: str) -> None:
  name = node.name
  iflist = node.get('interfaces',[])
  err_data = []
  for intf in iflist:
    if 'ospf' not in intf or intf.type != 'svi':
      continue
    err_data.append(f'Interface {intf.ifname} VRF {vname}')

  if err_data:
    report_quirk(
      f'node {name} cannot run OSPF on virtual-network (SVI) interfaces',
      quirk='svi_ospf',
      more_data=err_data,
      node=node)

class OS10(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_vlan_ospf(node,'default')
    for vname,vdata in node.get('vrfs',{}).items():
      check_vlan_ospf(node,vname)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'dellemc.os10')
