#
# IP Infusion OcNOS quirks
#
from box import Box

from ..augment import devices
from . import _Quirks, need_ansible_collection


class OCNOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    pass

  def check_config_sw(self, node: Box, topology: Box) -> None:
    if devices.get_node_group_var(node,'netlab_config_mode',topology.defaults) == 'netmiko':
      return                                        # netmiko does not need the Ansible collection
    need_ansible_collection(node,'ipinfusion.ocnos')
