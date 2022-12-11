#
# IS-IS transformation module
#
from box import Box

from . import _Module,_routing
from . import bfd
from .. import common
from ..augment import devices

def isis_unnumbered(node: Box, features: Box) -> bool:
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
      return False

  OK = True
  for l in node.get('interfaces',[]):
    unnum_v4 = 'unnumbered' in l or ('ipv4' in l and l.ipv4 is True)
    if unnum_v4 and \
        len(l.neighbors) > 1 and \
        not features.isis.unnumbered.network:
      common.error(
        f'Device {node.device} used on node {node.name} cannot run IS-IS over\n'+
        f'.. unnumbered multi-access interfaces (link {l.name})',
        common.IncorrectValue,
        'interfaces')
      OK = False

  return OK

class ISIS(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)

    if not isis_unnumbered(node,features):
      return

    bfd.multiprotocol_bfd_link_state(node,'isis')
    for l in node.get('interfaces',[]):
      if _routing.external(l,'isis') or not (l.get('ipv4',False) or l.get('ipv6',False)):
        l.pop('isis',None) # Don't run IS-IS on external interfaces, or l2-only
      else:
        _routing.passive(l,'isis')
        err = _routing.network_type(l,'isis',['point-to-point'])
        if err:
          common.error(f'{err}\n... node {node.name} link {l}')

    #
    # Final steps:
    #
    # * remove IS-IS from VRF interfaces
    # * Calculate address families
    # * Enable BFD
    # * Remove ISIS module if there are no IS-IS enabled global interfaces
    #
    _routing.remove_unaddressed_intf(node,'isis')
    _routing.remove_vrf_interfaces(node,'isis')
    _routing.routing_af(node,'isis')
    _routing.remove_unused_igp(node,'isis')
