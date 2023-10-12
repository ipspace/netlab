from box import Box
from netsim.utils import log,bgp as _bgp
from netsim import api
from netsim.augment import devices

_config_name = 'bgp.session'

def pre_link_transform(topology: Box) -> None:
  global _config_name
  # Error if BGP module is not loaded
  if 'bgp' not in topology.module:
    log.error(
      'BGP Module is not loaded.',
      log.IncorrectValue,
      _config_name)

'''
check_device_attribute_support -- using device BGP features, check whether the
device supports the attribute applied to a BGP neighbor
'''
def check_device_attribute_support(attr: str, ndata: Box, neigh: Box, topology: Box) -> None:
  global _config_name

  features = devices.get_device_features(ndata,topology.defaults)
  enabled = features.bgp.get(attr,None)
  if not enabled:
    log.error(
      f'Attribute {attr} used on BGP neighbor {neigh.name} is not supported by node {ndata.name} (device {ndata.device})',
      log.IncorrectValue,
      _config_name)

  if not isinstance(enabled,list):
    return

  if not topology.provider in enabled:
    log.error(
      f'Node {ndata.name} (device {ndata.device}) does not support BGP attribute {attr} when running with {topology.provider} provider',
      log.IncorrectValue,
      _config_name)

'''
Remove session attributes with local significance from BGP neighbors
because they are neighbors' attributes, not ours
'''
def cleanup_neighbor_attributes(ndata: Box, topology: Box) -> None:
  for ngb in _bgp.neighbors(ndata):
    for attr in topology.defaults.bgp.attributes.ebgp_utils.local:
      ngb.pop(attr,None)

'''
Copy local session attributes to BGP neighbors because we need
them there in the configuration templates
'''
def copy_local_attributes(ndata: Box, topology: Box) -> None:
  global _config_name

  # Iterate over all ebgp.utils link/interface attributes
  for (intf,ngb) in _bgp.intf_neighbors(ndata):
    for attr in topology.defaults.bgp.attributes.ebgp_utils.attr:
      attr_value = intf.get('bgp',{}).get(attr,None) or ndata.bgp.get(attr,None)
      if not attr_value:                                  # Attribute not defined in node or interface, move on
        continue

      check_device_attribute_support(attr,ndata,ngb,topology)
      ngb[attr] = attr_value                              # Set neighbor attribute from interface/node value
      api.node_config(ndata,_config_name)                 # And remember that we have to do extra configuration

'''
For platforms that collect tcp_ao secrets in global management profiles
we have to build a list of secrets so we can refer to them in neighbor
configurations
'''
def process_tcpao_password(neigh: Box, ndata: Box) -> None:
  global _config_name

  if not 'password' in neigh:
    log.error(
      f'BGP neighbor {neigh.name} on node {ndata.name} has TCP-AO configured without a password',
      log.MissingValue,
      _config_name)
    return
  
  pwd = neigh.password
  if not '_ao_secrets' in ndata.bgp:
    ndata.bgp._ao_secrets = []

  if not pwd in ndata.bgp._ao_secrets:
    ndata.bgp._ao_secrets.append(pwd)

def process_tcpao_secrets(ndata: Box,topology: Box) -> None:
  for ngb in _bgp.neighbors(ndata):
    if 'tcp_ao' in ngb:
      process_tcpao_password(ngb,ndata)

'''
Check whether a node runs BFD with any BGP neighbors
'''
def process_bfd_requests(ndata: Box, topology: Box) -> None:
  for ngb in _bgp.neighbors(ndata):
    if not 'bfd' in ngb:                                    # No BFD, no worries
      continue
    if not ngb.bfd:                                         # BFD set to False (or some similar stunt)
      ngb.pop('bfd')
      continue

    if not 'bfd' in ndata.module:                           # Do we have BFD enabled on this node?
      log.error(
        f'node {ndata.name} is running BFD with BGP neighbor {ngb.name} but does not use BFD module',
        log.IncorrectValue,
        _config_name)

'''
post_transform hook

As we're applying interface attributes to BGP sessions, we have to copy
interface BGP parameters supported by this plugin into BGP neighbor parameters
'''

def post_transform(topology: Box) -> None:
  for n, ndata in topology.nodes.items():
    if not 'bgp' in ndata.module:                           # Skip nodes not running BGP
      continue

    cleanup_neighbor_attributes(ndata,topology)             # Generic neighbor attribute cleanup
    copy_local_attributes(ndata,topology)
    process_tcpao_secrets(ndata,topology)
    process_bfd_requests(ndata,topology)