#
# Juniper cSRX quirks
#
from box import Box

from ..utils import log
from . import _Quirks, report_quirk

class CSRX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    from . import junos
