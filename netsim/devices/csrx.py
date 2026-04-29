#
# Juniper cSRX quirks
#
from box import Box

from ..utils import log
from . import _Quirks

class CSRX(_Quirks):

  @classmethod
  def device_quirks(self, node: Box, topology: Box) -> None:
    return
