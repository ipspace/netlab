#
# Juniper JunOS quirks
#

from . import junos
from box import Box

class vjunos_router(junos.JUNOS):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    super().device_quirks(node,topology)
