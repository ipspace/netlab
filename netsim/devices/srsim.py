#
# Nokia SR SIM quirks
#
from box import Box

from . import _Quirks, need_ansible_collection


class SRSIM(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    from .sros import SROS
    return SROS.device_quirks(node,topology)

  def check_config_sw(self, node: Box, topology: Box) -> None:
    need_ansible_collection(node,'nokia.grpc',version='1.0.2')
