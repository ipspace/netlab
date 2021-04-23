#
# IS-IS transformation module
#

from box import Box
import netaddr

from . import Module
from .. import common

class ISIS(Module):

  def node_post_transform(self,node,topology):
    for af in ['ipv4','ipv6']:
      if af in node.loopback:     # Address family enabled on loopback?
        node.isis[af] = True      # ... we need it in IS-IS
        continue

      for l in node.links:        # Scan all links
        if af in l:               # Do we have AF enabled on any of them?
          node.isis[af] = True    # Found it - we need it in IS-IS
          continue
