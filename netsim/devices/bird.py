#
# Bird quirks
#
from box import Box

from . import _Quirks
from ._common import check_daemon_dataplane_config, check_indirect_static_routes


class Bird(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    check_indirect_static_routes(node)
    check_daemon_dataplane_config(node,topology)
