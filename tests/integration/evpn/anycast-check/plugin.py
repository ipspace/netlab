"""
This plugin deals with devices that do not support
anycast gateway. It finds the default device, checks
whether it supports anycast gateway, and removes
"gateway" attribute from the VLANs if needed.
"""

from box import Box
from netsim.augment.devices import get_device_features
from netsim.data import get_box
from netsim.modules import get_effective_module_attribute
from netsim.utils import log

def pre_transform(topology: Box) -> None:
  gw_proto = get_effective_module_attribute('gateway.protocol',topology=topology,defaults=topology.defaults)
  if gw_proto != 'anycast':
    return

  def_device = topology.defaults.device
  node = get_box({'device': def_device})
  features = get_device_features(node,topology.defaults)

  if 'anycast' in features.get('gateway.protocol'):
    topology.validate.pop('anycast',None)
    return

  for vname,vdata in topology.get('vlans',{}).items():
    if not isinstance(vdata,Box):
      continue
    gw_data = vdata.get('gateway',None)
    if gw_data is None:
      continue

    if gw_data is not True:
      continue

    log.warning(
      text=f'Removing anycast gateway from VLAN {vname}',
      more_hints=f'Device {def_device} does not support anycast gateways',
      module='anycast')
    vdata.pop('gateway',None)

    if 'anycast' in topology.validate:
      topology.validate.anycast.fail = f'Device {def_device} does not support anycast gateways'
      topology.validate.anycast.level = 'warning'
