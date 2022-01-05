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

    # Determine the IS-IS network type for each interface, based on number of neighbors
    # and whether the interface is passive
    for l in node.interfaces:
        if 'isis' in l:
            l.isis.network_type_p2p = len(l.get('neighbors',[])) == 1
            l.isis.passive = l.type == "stub" or l.get('role',"") in ["stub","passive"]
