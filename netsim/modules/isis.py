#
# IS-IS transformation module
#
from box import Box

from . import _Module
from . import bfd

class ISIS(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    self.set_af_flag(node,node.isis)

    bfd.multiprotocol_bfd_link_state(node,'isis')
