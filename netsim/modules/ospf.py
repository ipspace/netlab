#
# OSPF transformation module
#
import typing

from box import Box

from . import _Module,_routing
from . import bfd
from ..utils import log
from ..augment import devices

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
def ospf_unnumbered(node: Box, features: Box) -> bool:
  OK = True

  for l in node.get('interfaces',[]):
    is_unnumbered = \
      'unnumbered' in l or \
      ('ipv4' in l and isinstance(l.ipv4,bool) and l.ipv4)
    if is_unnumbered and 'ospf' in l:
      node.ospf.unnumbered = True
      if len(l.get('neighbors',[])) > 1:
        log.error(
          f'OSPF does not work over multi-access unnumbered IPv4 interfaces: node {node.name} link {l.name}',
          log.IncorrectValue,
          'ospf')
        OK = False
      elif not len(l.get('neighbors',[])):
        log.error(
          f'Configuring OSPF on an unnumbered stub interface makes no sense: node {node.name} link {l.name}',
          log.IncorrectValue,
          'ospf')
        OK = False

  if 'unnumbered' in node.ospf:
    if not features.ospf.unnumbered:
      log.error(
        f'Device {node.device} used on node {node.name} cannot run OSPF over unnumbered interface',
        log.IncorrectValue,
        'interfaces')
      OK = False

  return OK

class OSPF(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)

    _routing.router_id(node,'ospf',topology.pools)
    
    # If strict BFD is requested, check if the node supports it
    if isinstance(node.get('ospf.bfd',None),Box) and node.get('ospf.bfd.strict',False):
      if features.get('ospf.strict_bfd',False):
        if 'bfd' in node.get('module',[]):
          node.ospf.strict_bfd = True
          node.ospf.strict_bfd_delay = node.get('ospf.bfd.strict_delay',0)
        else:
          log.error(
            f'{node.name} uses strict BFD with OSPF without enabling the "bfd" module',
            log.IncorrectValue,
            'ospf')
      else:
        log.error(
          f'{node.name} uses strict BFD with OSPF which is not supported by {node.device} device',
          log.IncorrectValue,
          'ospf')

    bfd.bfd_link_state(node,'ospf')

    #
    # Cleanup routing protocol from external/disabled interfaces
    for intf in node.get('interfaces',[]):
      if not _routing.external(intf,'ospf'):                # Remove external interfaces from OSPF process
        _routing.passive(intf,'ospf',topology)              # Set passive flag on other OSPF interfaces
        err = _routing.network_type(intf,'ospf',['point-to-point','point-to-multipoint','broadcast','non-broadcast'])
        if err:
          log.error(f'{err}\n... node {node.name} link {intf}')

    if not ospf_unnumbered(node,features):
      return

    #
    # Final steps:
    # * move OSPF-enabled VRF interfaces into VRF dictionary
    # * Calculate address families
    # * Enable BFD
    # * Remove OSPF module if there are no OSPF-enabled global or VRF interfaces
    #
    _routing.remove_unaddressed_intf(node,'ospf')
    _routing.build_vrf_interface_list(node,'ospf',topology)
    _routing.routing_af(node,'ospf')
    _routing.remove_vrf_routing_blocks(node,'ospf')
    _routing.remove_unused_igp(node,'ospf')
