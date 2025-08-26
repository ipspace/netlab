#
# A no-op output module, useful when testing new features
#

from box import Box

from . import _TopologyOutput


class NONE(_TopologyOutput):

  def write(self, topo: Box) -> None:
    pass
