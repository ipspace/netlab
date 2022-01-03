#
# OSPF transformation module
#
import typing

from box import Box

from . import _Module
from . import bfd

class OSPF(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    bfd.bfd_link_state(node,'ospf')
    if not 'links' in node:
      return

    # We need to set ospf.unnumbered if we happen to have OSPF running over an unnumbered
    # link -- Arista EOS needs an extra nerd knob to make it work
    #
    for l in node.links:                                         # Scan all links 
      if 'unnumbered' in l:                                      # ... old style unnumbered link
        node.ospf.unnumbered = True
        break                                                    # No need to go any further
      elif 'ipv4' in l and isinstance(l.ipv4,bool) and l.ipv4:   # New-style unnumbered link: ipv4 set to True
        node.ospf.unnumbered = True
        break
      