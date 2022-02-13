#
# IS-IS transformation module
#
from box import Box

from . import _Module,_routing
from . import bfd
from .. import common
from ..augment import devices

class ISIS(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    _routing.routing_af(node,'isis')

    bfd.multiprotocol_bfd_link_state(node,'isis')
    features = devices.get_device_features(node,topology.defaults)

    for af in ('ipv4','ipv6'):
      is_unnumbered = False
      for l in node.get('interfaces',[]):
        is_unnumbered = is_unnumbered or \
          'unnumbered' in l or \
          (af in l and isinstance(l[af],bool) and l[af])

      if is_unnumbered and not features.isis.unnumbered[af]:
        common.error(
          f'Device {node.device} used on node {node.name} cannot run IS-IS over {"unnumbered" if af == "ipv4" else "LLA"} {af} interfaces',
          common.IncorrectValue,
          'interfaces')

    for l in node.get('interfaces',[]):
      unnum_v4 = 'unnumbered' in l or ('ipv4' in l and isinstance(l.ipv4,bool) and l.ipv4)
      if unnum_v4 and \
          len(l.neighbors) > 1 and \
          features.isis.unnumbered.ipv4 and \
          not features.isis.unnumbered.network:
        common.error(
          f'Device {node.device} used on node {node.name} cannot run IS-IS over\n'+
          f'.. unnumbered multi-access interfaces (link {l.name})',
          common.IncorrectValue,
          'interfaces')
      elif _routing.external(l,'isis') or not (l.get('ipv4',False) or l.get('ipv6',False)):
        l.pop('isis',None) # Don't run IS-IS on external interfaces, or l2-only
      else:
        _routing.passive(l,'isis')
        err = _routing.network_type(l,'isis',['point-to-point'])
        if err:
          common.error(f'{err}\n... node {node.name} link {l}')
