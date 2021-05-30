#
# OSPF transformation module
#
import typing

from box import Box

from . import _Module

class OSPF(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    if not 'links' in node:
      return

    for l in node.links:             # Scan all links
      if 'unnumbered' in l:          # Do we have an unnumbered link?
        node.ospf.unnumbered = True  # Found it - set a flag for Arista EOS hack
        break                        # No need to go any further
