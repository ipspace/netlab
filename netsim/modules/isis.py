#
# IS-IS transformation module
#
from box import Box

from . import _Module,_routing
from . import bfd
from ..utils import log
from ..augment import devices
from ..data import validate

def isis_unnumbered(node: Box, features: Box) -> bool:
  for af in ('ipv4','ipv6'):
    is_unnumbered = False
    for l in node.get('interfaces',[]):
      is_unnumbered = is_unnumbered or (af in l and isinstance(l[af],bool) and l[af])

    if is_unnumbered and not features.isis.unnumbered[af]:
      log.error(
        f'Device {node.device} used on node {node.name} cannot run IS-IS over {"unnumbered" if af == "ipv4" else "LLA"} {af} interfaces',
        log.IncorrectValue,
        'interfaces')
      return False

  OK = True
  for l in node.get('interfaces',[]):
    unnum_v4 = l.get('ipv4',None) is True
    if unnum_v4 and \
        len(l.neighbors) > 1 and \
        not features.isis.unnumbered.network:
      log.error(
        f'Device {node.device} (node {node.name}) cannot run IS-IS over unnumbered multi-access link {l.name}',
        log.IncorrectValue,
        'interfaces')
      OK = False

  return OK

class ISIS(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    isis_type = [ 'level-1', 'level-2', 'level-1-2' ]
    features = devices.get_device_features(node,topology.defaults)

    validate.must_be_string(
      node,'isis.type',f'nodes.{node.name}',module='isis',valid_values=isis_type)
    if not isis_unnumbered(node,features):
      return

    if 'sr' in node.module:
      _routing.router_id(node,'isis',topology.pools)

    bfd.multiprotocol_bfd_link_state(node,'isis')
    for l in node.get('interfaces',[]):
      if _routing.external(l,'isis') or not (l.get('ipv4',False) or l.get('ipv6',False)):
        l.pop('isis',None) # Don't run IS-IS on external interfaces, or l2-only
      else:
        _routing.passive(l,'isis',topology)
        err = _routing.network_type(l,'isis',['point-to-point'])
        if err:
          log.error(f'{err}\n... node {node.name} link {l}')
      validate.must_be_string(
        l,'isis.type',f'nodes.{node.name}.interfaces.{l.ifname}',module='isis',valid_values=isis_type)

    _routing.igp_post_transform(node,topology,proto='isis',vrf_aware=True)
    _routing.check_vrf_protocol_support(node,'isis','ipv4','isis',topology)
    _routing.check_vrf_protocol_support(node,'isis','ipv6','isis',topology)

    # Finally, change the VRF IS-IS instance name to the VRF name to make it unique
    #
    for vname,vdata in node.get('vrfs',{}).items():
      if vdata.get('isis.instance',None):
        vdata.isis.instance = vname
