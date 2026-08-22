#
# dnsmasq quirks
#
from box import Box

from . import _Quirks
from .linux import etc_resolv_mapping


class Dnsmasq(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    etc_resolv_mapping(node,topology)
