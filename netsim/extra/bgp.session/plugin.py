from box import Box
from netsim.utils import log
from netsim import api
from netsim.augment import devices

def pre_link_transform(topology: Box) -> None:
  # Error if BGP module is not loaded
  if 'bgp' not in topology.module:
    log.error(
      'BGP Module is not loaded.',
      log.IncorrectValue,
      'ebgp_utils')

'''
check_device_attribute_support -- using device BGP features, check whether the
device supports the attribute applied to a BGP neighbor
'''
def check_device_attribute_support(attr: str, ndata: Box, neigh: Box, topology: Box) -> None:
  features = devices.get_device_features(ndata,topology.defaults)
  enabled = features.bgp.get(attr,None)
  if not enabled:
    log.error(
      f'Attribute {attr} used on BGP neighbor {neigh.name} is not supported by node {ndata.name} (device {ndata.device})',
      log.IncorrectValue,'ebgp.utils')

  if not isinstance(enabled,list):
    return

  if not topology.provider in enabled:
    log.error(
      f'Node {ndata.name} (device {ndata.device}) does not support BGP attribute {attr} when running with {topology.provider} provider',
      log.IncorrectValue,'ebgp.utils')

'''
Remove session attributes with local significance from BGP neighbors
because they are neighbors' attributes, not ours
'''
def cleanup_neighbor_attributes(ndata: Box, topology: Box) -> None:
  for attr in topology.defaults.bgp.attributes.ebgp_utils.local:
    for neigh in ndata.get('bgp', {}).get('neighbors', []):
      neigh.pop(attr,None)

    for vdata in ndata.get('vrfs',{}):
      if not vdata.get('bgp.neighbors',None):
        continue
      for neigh in vdata.bgp.neighbors:
        neigh.pop(attr,None)

'''
Copy local session attributes to BGP neighbors because we need
them there in the configuration templates
'''
def copy_local_attributes(ndata: Box, topology: Box) -> None:
  config_name = api.get_config_name(globals())              # Get the plugin configuration name
  # Iterate over all ebgp.utils link/interface attributes
  for intf in ndata.interfaces:
    for attr in topology.defaults.bgp.attributes.ebgp_utils.attr:
      attr_value = intf.get('bgp',{}).get(attr,None) or ndata.bgp.get(attr,None)
      if not attr_value:                                  # Attribute not defined in node or interface, move on
        continue

      # Iterate over all BGP neighbors trying to find neighbors on this interface
      for neigh in ndata.get('bgp', {}).get('neighbors', []):
        if neigh.type == 'ebgp' and neigh.ifindex == intf.ifindex:
          check_device_attribute_support(attr,ndata,neigh,topology)
          neigh[attr] = attr_value                        # Found the neighbor, set neighbor attribute
          api.node_config(ndata,config_name)              # And remember that we have to do extra configuration

      if 'vrf' not in intf:                               # Not a VRF interface?
          continue                                         # ... great, move on

      # Now do the same 'copy interface attribute to neighbors' thing for VRF neighbors
      for neigh in ndata.vrfs[intf.vrf].get('bgp', {}).get('neighbors', []):
        if neigh.ifindex == intf.ifindex and neigh.type == 'ebgp':
          neigh[attr] = attr_value                        # Found the neighbor, set neighbor attribute
          api.node_config(ndata,config_name)              # And remember that we have to do extra configuration

'''
For platforms that collect tcp_ao secrets in global management profiles
we have to build a list of secrets so we can refer to them in neighbor
configurations
'''
def process_tcpao_password(neigh: Box, ndata: Box) -> None:
  if not 'password' in neigh:
    log.error(
      f'BGP neighbor {neigh.name} on node {ndata.name} has TCP-AO configured without a password',
      log.MissingValue,'ebgp.utils')
    return
  
  pwd = neigh.password
  if not '_ao_secrets' in ndata.bgp:
    ndata.bgp._ao_secrets = []

  if not pwd in ndata.bgp._ao_secrets:
    ndata.bgp._ao_secrets.append(pwd)

def process_tcpao_secrets(ndata: Box,topology: Box) -> None:
  for neigh in ndata.get('bgp', {}).get('neighbors', []):
    if 'tcp_ao' in neigh:
      process_tcpao_password(neigh,ndata)

  for vdata in ndata.get('vrfs',{}):
    if not vdata.get('bgp.neighbors',None):
      continue
    for neigh in vdata.bgp.neighbors:
      if 'tcp_ao' in neigh:
        process_tcpao_password(neigh,ndata)

'''
post_transform hook

As we're applying interface attributes to BGP sessions, we have to copy
interface BGP parameters supported by this plugin into BGP neighbor parameters
'''

def post_transform(topology: Box) -> None:
  config_name = api.get_config_name(globals())              # Get the plugin configuration name

  for n, ndata in topology.nodes.items():
    if not 'bgp' in ndata.module:                           # Skip nodes not running BGP
      continue

    cleanup_neighbor_attributes(ndata,topology)             # Generic neighbor attribute cleanup
    copy_local_attributes(ndata,topology)
    process_tcpao_secrets(ndata,topology)