#
# IS-IS transformation module
#
from box import Box

from . import _Module,igp_network_type,igp_external,igp_set_passive
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
      has_ipv4 = unnum_v4 or ('ipv4' in l and (not isinstance(l.ipv4,bool) or l.ipv4))
      has_ipv6 = ('ipv6' in l and (not isinstance(l.ipv6,bool) or l.ipv6))
      if unnum_v4 and \
          len(l.neighbors) > 1 and \
          topology.defaults.devices[node.device].features.isis.unnumbered.ipv4 and \
          not topology.defaults.devices[node.device].features.isis.unnumbered.network:
        common.error(
          f'Device {node.device} used on node {node.name} cannot run IS-IS over\n'+
          f'.. unnumbered multi-access interfaces (link {l.name})',
          common.IncorrectValue,
          'interfaces')
      elif l.get('role',"") == "external" or not (has_ipv4 or has_ipv6):
        l.pop('isis',None) # Don't run IS-IS on external interfaces, or l2-only
      else:
        l.isis.passive = l.type == "stub" or l.get('role',"") in ["stub","passive"]   # passive interfaces: stub or role stub/passive
        err = igp_network_type(l,'isis',['point-to-point'])
        if err:
          common.error(f'{err}\n... node {node.name} link {l}')
