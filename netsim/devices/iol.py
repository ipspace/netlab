#
# Cisco IOS-XE quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk
from .iosv import check_ripng_passive


def check_srv6_sid(node: Box, topology: Box) -> None:
  if node.get('srv6.allocate_loopback',False):
    report_quirk(
      f'SRv6 SID on Cisco IOS-XE cannot overlap with the loopback address',
      node,
      quirk='srv6.sid',
      more_hints=['Set the srv6.allocate_loopback parameter to False'],
      category=log.IncorrectValue)

class IOSXE(_Quirks):
  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_ripng_passive(node,topology)
    check_srv6_sid(node,topology)
