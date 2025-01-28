#
# Cisco IOS-XE quirks
#
from box import Box

from . import _Quirks
from .iosv import common_ios_quirks,check_ripng_passive

class IOSXE(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_ripng_passive(node,topology)
