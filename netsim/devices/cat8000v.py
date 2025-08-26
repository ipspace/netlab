#
# Cisco IOS-XE quirks
#
from box import Box

from .iol import IOSXE as _IOSXE
from .iosvl2 import check_reserved_vlans


class IOSL2(_IOSXE):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)
    check_reserved_vlans(node,topology)
