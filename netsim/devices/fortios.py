#
# FortiOS quirks
#
from box import Box

from . import _Quirks
from ._common import check_indirect_static_routes

class FortiOS(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
