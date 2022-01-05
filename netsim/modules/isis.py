#
# IS-IS transformation module
#
from box import Box

from . import _Module
from . import bfd
from .. import common

class ISIS(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    self.set_af_flag(node,node.isis)

    bfd.multiprotocol_bfd_link_state(node,'isis')

    for af in ('ipv4','ipv6'):
      is_unnumbered = False
      for l in node.get('interfaces',[]):
        is_unnumbered = is_unnumbered or \
          'unnumbered' in l or \
          (af in l and isinstance(l[af],bool) and l[af])

      if is_unnumbered and not topology.defaults.devices[node.device].features.isis.unnumbered[af]:
        common.error(
          f'Device {node.device} used on node {node.name} cannot run IS-IS over {"unnumbered" if af == "ipv4" else "LLA"} {af} interfaces',
          common.IncorrectValue,
          'interfaces')

    for l in node.get('interfaces',[]):
      unnum_v4 = 'unnumbered' in l or ('ipv4' in l and isinstance(l.ipv4,bool) and l.ipv4)
      if unnum_v4 and \
          len(l.neighbors) > 1 and \
          topology.defaults.devices[node.device].features.isis.unnumbered.ipv4 and \
          not topology.defaults.devices[node.device].features.isis.unnumbered.network:
        common.error(
          f'Device {node.device} used on node {node.name} cannot run IS-IS over\n'+
          f'.. unnumbered multi-access interfaces (link {l.name})',
          common.IncorrectValue,
          'interfaces')
      else:
        # Determine the IS-IS network type for each interface, based on number of neighbors
        # and whether the interface is passive
        l.isis.network_type_p2p = len(l.get('neighbors',[])) == 1
        l.isis.passive = l.type == "stub" or l.get('role',"") in ["stub","passive"]
