#
# IS-IS transformation module
#
import re

from box import Box

from ..augment import devices
from ..utils import log
from . import _Module, _routing, bfd

"""
Create net/area/system_id items from a subset of parameters
"""
def isis_net(i_data: Box, node: Box) -> bool:
  if 'net' in i_data:
    n_parsed = re.fullmatch('([0-9a-f.]+?)\\.((?:[0-9a-f]{4}\\.){3})[0]{2}',i_data.net)
    if not n_parsed:
      log.error(
        'net attribute is not a NSAP with zero n-selector',
        category=log.IncorrectValue,
        module='isis')
      return False
    i_data.area = n_parsed[1]
    i_data.system_id = n_parsed[2].rstrip('.')
  else:
    if 'system_id' not in i_data:
      i_data.system_id = '0000.0000.%04d' % node.id
    if 'area' not in i_data:
      log.error(
        f'isis.area or isis.net is not defined on node {node.name}',
        category=log.MissingValue,
        module='isis')
      return False
    i_data.net = f'{i_data.area}.{i_data.system_id}.00'

  return True

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
    features = devices.get_device_features(node,topology.defaults)

    if not isis_unnumbered(node,features):
      return

    if not isis_net(node.isis,node):
      return

    if 'sr' in node.module:
      _routing.router_id(node,'isis',topology.pools)

    isis_ct_intf = []
    for l in node.get('interfaces',[]):
      if _routing.external(l,'isis') or not (l.get('ipv4',False) or l.get('ipv6',False)):
        l.pop('isis',None) # Don't run IS-IS on external interfaces, or l2-only
      else:
        _routing.passive(l,'isis',topology)
        err = _routing.network_type(l,'isis',['point-to-point'])
        if err:
          log.error(f'{err}\n... node {node.name} link {l}')
        if 'isis.type' in l and not features.isis.circuit_type:
          isis_ct_intf.append(l.ifname)

    if isis_ct_intf:
      log.warning(
        text=f'Device {node.device} (node {node.name}) does not support IS-IS circuit type',
        flag='circuit_type',
        module='isis',
        more_data=f'Used on interface(s) {",".join(isis_ct_intf)}',
        category=log.IncorrectAttr)

    _routing.igp_post_transform(node,topology,proto='isis',vrf_aware=True)
    bfd.multiprotocol_bfd_link_state(node,'isis')
    _routing.check_vrf_protocol_support(node,'isis','ipv4','isis',topology)
    _routing.check_vrf_protocol_support(node,'isis','ipv6','isis',topology)

    # Finally, change the VRF IS-IS instance name to the VRF name to make it unique
    #
    for vname,vdata in node.get('vrfs',{}).items():
      if 'isis' in vdata:
        if vdata.get('isis.instance',None):
          vdata.isis.instance = vname
