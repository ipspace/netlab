#
# Cisco IOS-XE quirks
#

from box import Box

from .iol import IOSXE as _IOSXE
from .iosv import use_paramiko


class CSR(_IOSXE):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)
    use_paramiko(node,topology)
