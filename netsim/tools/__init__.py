#
# Dynamic output framework
# 
# Individual output routines are defined in modules within this directory inheriting
# TopologyOutput class and replacing or augmenting its methods (most commonly, write)
#

import re
import typing

# Related modules
from box import Box

from ..utils import log
from ..utils.callback import Callback


class _ToolOutput(Callback):
  def __init__(self) -> None:
    pass

  @classmethod
  def load(self, module: str) -> typing.Optional['_ToolOutput']:
    module_name = __name__+"."+module
    obj = self.find_class(module_name)
    if obj:
      return obj()
    else:
      return None

  def write(self, topology: Box, fmt: str) -> str:
    log.fatal('someone called the "write" method of ToolOutput abstract class')
    return ""