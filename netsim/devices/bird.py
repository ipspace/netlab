#
# Bird quirks
#
from box import Box

from ..augment import devices
from ..data import append_to_list
from . import _Quirks
from ._common import check_indirect_static_routes


class Bird(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    if devices.get_provider(node,topology) == 'clab':
      append_to_list(node,'config','config-done')
