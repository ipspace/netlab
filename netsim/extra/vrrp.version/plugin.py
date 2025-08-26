from box import Box

from netsim import api
from netsim.augment import devices
from netsim.utils import log

_config_name = 'vrrp.version'
_requires    = [ 'gateway' ]

def pre_link_transform(topology: Box) -> None:
  global _config_name
  # Error if gateway module is not loaded
  if 'gateway' not in topology.module:
    log.error(
      'gateway module is not loaded.',
      log.IncorrectValue,
      _config_name)

'''
post_transform hook

Apply plugin config to nodes running gateway.vrrp for devices that support this plugin
'''
def post_transform(topology: Box) -> None:
  global _config_name
  for node in topology.nodes.values():
    if 'gateway' not in node.get('module',[]):         # Skip nodes not running gateway
      continue
    elif 'vrrp' not in node.gateway:
      continue

    features = devices.get_device_features(node,topology.defaults)
    if 'gateway.vrrp.version' in features:
      api.node_config(node,_config_name)               # Remember that we have to do extra configuration
    else:
      log.error( f'node {node.name} does not support the vrrp.version plugin.',
        log.IncorrectValue,
        _config_name)
