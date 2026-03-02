"""
This plugin sets the evpn.transport to the first transport
supported by the device under test. It's used in control-plane
tests (BGP RR) for devices that do not support VXLAN transport
(for example, CSR1000v or IOS XR).
"""

from box import Box

from netsim.augment.devices import get_device_features
from netsim.data import append_to_list, get_box
from netsim.utils import log


def init(topology: Box) -> None:
  def_device = topology.defaults.device               # Get features of the default device
  node = get_box({'device': def_device})
  features = get_device_features(node,topology.defaults)
  if 'evpn.transport' not in features:                # Does the device specify available EVPN transports?
    return

  transport = features.evpn.transport[0]
  if transport == 'vxlan':                            # Is the default transport VXLAN?
    return                                            # ... cool, we're good to go.

  topology.evpn.transport = transport
  swg = topology.groups.switches
  append_to_list(swg,'module',transport)
  if transport == 'mpls':
    swg.mpls.ldp = True

  log.warning(
    text=f'Setting EVPN transport to {transport}',
    more_hints=f'Device {def_device} does not support VXLAN as EVPN transport',
    module='evpn')
