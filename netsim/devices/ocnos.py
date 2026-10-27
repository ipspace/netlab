#
# IP Infusion OcNOS quirks
#
from box import Box

from ..augment import devices
from ..utils import log
from . import _Quirks, need_ansible_collection, report_quirk


def check_vlan_1(node: Box) -> None:
  '''
  OcNOS creates VLAN 1 with the bridge and rejects any attempt to use it: it cannot
  be added to the VLAN database, used as an access VLAN or a native VLAN, or added to a trunk
  '''
  vlan_1 = [ vname for vname,vdata in node.get('vlans',{}).items() if vdata.get('id',None) == 1 ]
  if not vlan_1:
    return

  intf_list = [ intf.ifname for intf in node.interfaces
                  if intf.get('vlan.access_id',None) == 1 or 1 in intf.get('vlan.trunk_id',[]) ]
  report_quirk(
    text=f'OcNOS cannot use VLAN 1 (VLAN {vlan_1[0]}, node {node.name})',
    more_data=f'VLAN 1 is used on interface(s) {", ".join(intf_list)}' if intf_list else None,
    more_hints=['Use a different VLAN ID'],
    node=node,
    quirk='vlan_1',
    category=log.IncorrectValue)


class OCNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    if 'vlan' in node.get('module',[]):
      check_vlan_1(node)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    if devices.get_node_group_var(node,'netlab_config_mode',topology.defaults) == 'netmiko':
      return                                        # netmiko does not need the Ansible collection
    need_ansible_collection(node,'ipinfusion.ocnos')
