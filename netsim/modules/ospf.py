#
# OSPF transformation module
#
import typing

from box import Box

from . import _Module
from . import bfd
from .. import common

class OSPF(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    bfd.bfd_link_state(node,'ospf')

    # We need to set ospf.unnumbered if we happen to have OSPF running over an unnumbered
    # link -- Arista EOS needs an extra nerd knob to make it work
    #
    # An interface can be unnumbered if it has the 'unnumbered' flag set or if it
    # has IPv4 enabled but no IPv4 address (ipv4: true)
    #
    # While doing that, we also check for the number of neighbors on unnumbered interfaces
    # and report an error if there are none (in which case the interface should not be unnumbered)
    # or more than one (in which case OSPF won't work)
    #
    for l in node.get('interfaces',[]):
      is_unnumbered = \
        'unnumbered' in l or \
        ('ipv4' in l and isinstance(l.ipv4,bool) and l.ipv4)
      if is_unnumbered:
        node.ospf.unnumbered = True
        if len(l.get('neighbors',[])) > 1:
          common.error(
            f'OSPF does not work over multi-access unnumbered IPv4 interfaces: node {node.name} link {l.name}',
            common.IncorrectValue,
            'ospf')
