#
# Dell OS10 quirks
#
from box import Box

from . import _Quirks,need_ansible_collection
from ..utils import log
from ..augment import devices

def check_vlan_ospf(name: str, iflist: list, vname: str) -> None:
  err_data = []
  for intf in iflist:
    if 'ospf' not in intf or intf.type != 'svi':
      continue
    err_data.append(f'Interface {intf.ifname} VRF {vname}')

  if err_data:
    log.error(
      f'Dell OS10 (node {name}) cannot run OSPF on virtual-network (SVI) interfaces',
      category=log.IncorrectValue,
      more_data=err_data,
      module='ospf')

class OS10(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_vlan_ospf(node.name,node.get('interfaces',[]),'default')
    for vname,vdata in node.get('vrfs',{}).items():
      check_vlan_ospf(node.name,vdata.get('ospf.interfaces',[]),vname)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'dellemc.os10')
