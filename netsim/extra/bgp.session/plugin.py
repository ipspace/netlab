import typing
from box import Box
from netsim.utils import log,bgp as _bgp
from netsim import api
from netsim.augment import devices

_config_name = 'bgp.session'
_requires    = [ 'bgp' ]

def pre_link_transform(topology: Box) -> None:
  global _config_name
  # Error if BGP module is not loaded
  if 'bgp' not in topology.module:
    log.error(
      'BGP Module is not loaded.',
      log.IncorrectValue,
      _config_name)

'''
Get a list of attributes to apply to IBGP or EBGP sessions
'''
def get_attribute_list(apply_list: typing.Any, topology: Box) -> list:
  if apply_list is None or apply_list is True or (isinstance(apply_list,list) and '*' in apply_list):
    return topology.defaults.bgp.attributes.session.attr

  return list(apply_list)

'''
Apply attributes supported by bgp.session plugin to a single neighbor
Returns False is some of the attributes are not supported
'''
def apply_neighbor_attributes(node: Box, ngb: Box, intf: typing.Optional[Box], apply_list: list, topology: Box) -> bool:
  global _config_name

  OK = True
  for attr in apply_list:
    attr_value = None if intf is None else \
                 intf.get('bgp',{}).get(attr,None)      # Get attribute value from interface if specified
    attr_value = attr_value or node.bgp.get(attr,None)  # ... and try node attribute value if there's no interface value
    if not attr_value:                                  # Attribute not defined in node or interface, move on
      continue

    # Check that the node(device) supports the desired attribute
    OK = OK and _bgp.check_device_attribute_support(attr,node,ngb,topology,_config_name)
    ngb[attr] = attr_value                              # Set neighbor attribute from interface/node value
    api.node_config(node,_config_name)                  # And remember that we have to do extra configuration

  return OK

'''
Copy local session attributes to BGP neighbors because we need
them there in the configuration templates
'''
def copy_local_attributes(ndata: Box, topology: Box) -> None:
  apply = ndata.get('bgp.session.apply',{ 'ebgp': None })     # By default we apply all session attributes only to EBGP neighbors

  OK = True
  if 'ibgp' in apply:                                         # Do we apply session attributes to IBGP neighbors?
    apply_list = get_attribute_list(apply.ibgp,topology)      # Get attributes to apply to IBGP neighbors
    for ngb in  _bgp.neighbors(ndata,select=['ibgp']):        # Iterate over all neighbors using node attributes
      OK = OK and apply_neighbor_attributes(ndata,ngb,None,apply_list,topology)

  if not OK:                                                  # Skip the second step if we encountered unsupported device
    return                                                    # ... doesn't make sense to throw the same error(s) twice

  if 'ebgp' in apply:                                         # Do we apply session attributes to EBGP neighbors?
    apply_list = get_attribute_list(apply.ebgp,topology)      # Get attributes to apply to IBGP neighbors

    # Iterate over neighbors that have associated interfaces (all EBGP neighbors are supposed to be directly connected)
    for (intf,ngb) in _bgp.intf_neighbors(ndata,select=['ebgp']):
      apply_neighbor_attributes(ndata,ngb,intf,apply_list,topology)

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

    _bgp.cleanup_neighbor_attributes(ndata,topology,topology.defaults.bgp.attributes.session.attr)
    copy_local_attributes(ndata,topology)
    process_tcpao_secrets(ndata,topology)
    process_bfd_requests(ndata,topology)