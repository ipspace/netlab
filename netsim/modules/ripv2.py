#
# RIPv2/RIPng transformation module
#

from box import Box

from ..augment import devices
from . import _Module, _routing, bfd

"""
adjust_rip_timers: Make sure all three timers are set if at least one of the 'ripv2.timers'
attributes are set (data validation makes sure we're not dealing with bogus attributes)

Having consistent set of three timers makes the configuration templates cleaner and avoids
dealing with device-specific defaults (some devices accept less than three timers)

Finally: it seems like 'update' might be a valid method for the dictionary object,
so we're using traditional dict expression to access the update timer.
"""
def adjust_rip_timers(rip_data: Box) -> None:
  if 'timers' not in rip_data:
    return

  if 'update' not in rip_data.timers:             # If we want to set timers, we need the update timer
    rip_data.timers['update'] = 30                # ... if it's missing, we'll use the default value

  if 'timeout' not in rip_data.timers:            # RFC says the default timeout value is 6 times the update timer
    rip_data.timers.timeout = rip_data.timers['update'] * 6

  if 'garbage' not in rip_data.timers:            # ... and the default GC value is 4 times the update timer
    rip_data.timers.garbage = rip_data.timers['update'] * 4

class RIPv2(_Module):

  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)

    _routing.router_id(node,'ripv2',topology.pools)
    
    bfd.bfd_link_state(node,'ripv2')

    #
    # Cleanup routing protocol from external/disabled interfaces
    for intf in node.get('interfaces',[]):
      if not _routing.external(intf,'ripv2'):                   # Remove external interfaces from RIPv2 process
        _routing.passive(intf,'ripv2',topology,features,node)   # Set passive flag on other RIPv2 interfaces

    _routing.igp_post_transform(node,topology,proto='ripv2',vrf_aware=True)
    _routing.check_vrf_protocol_support(node,proto='ripv2',af='ipv4',feature='ripv2',topology=topology)
    _routing.check_vrf_protocol_support(node,proto='ripv2',af='ipv6',feature='ripng',topology=topology)
    for rip_data in _routing.routing_protocol_data(node,'ripv2'):
      adjust_rip_timers(rip_data)
