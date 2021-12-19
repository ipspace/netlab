#
# A no-op output module, useful when testing new features
#
import typing

from box import Box

from .. import common
from . import _TopologyOutput

class NONE(_TopologyOutput):

  def write(self, topo: Box) -> None:
    pass
