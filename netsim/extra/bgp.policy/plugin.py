import typing
from box import Box
from netsim.utils import log,bgp as _bgp
from netsim import api,data
from netsim.augment import devices

_config_name = 'bgp.policy'

#_requires    = [ 'bgp' ]

'''
append_policy_attribute

* Apply a standalone policy attribute to an input or output policy
* If the policy does not exist, create a single-entry placeholder policy

The plugin does not support direct definition of BGP policies yet, but we're
trying to guess what the data structure should be to minimize the impact on
configuration templates
'''

def append_policy_attribute(ngb: Box, attr: str, direction: str, attr_value: typing.Any) -> None:
  if not ngb.policy[direction]:                         # Create an empty policy list if needed
    ngb.policy[direction] = [ data.get_empty_box() ]

  for p_entry in ngb.policy[direction]:                 # Add a 'set' entry to every policy element
    p_entry.set[attr] = attr_value                      # ... to cope with route-map limitations

_attr_list: list = []
_direct: list = []
_compound: dict = {}

'''
Apply attributes supported by bgp.policy plugin to a single neighbor
Returns True if at least some relevant attributes were found
'''
def apply_policy_attributes(node: Box, ngb: Box, intf: Box, topology: Box) -> bool:
  global _config_name,_direct,_compound,_attr_list

  if not _attr_list:                                    # Premature optimization: build the attribute lists only once
    _direct   = topology.defaults.bgp.attributes.p_attr.direct
    _compound = topology.defaults.bgp.attributes.p_attr.compound
    _attr_list = _direct + list(_compound.keys())

  Found = False
  for attr in _attr_list:
    attr_value = intf.get('bgp',{}).get(attr,None)      # Get attribute value from interface
    if not attr_value:                                  # Attribute not defined on interface, move on
      continue

    # Check that the node(device) supports the desired attribute
    if not _bgp.check_device_attribute_support(attr,node,ngb,topology,_config_name):
      continue

    Found = True
    ngb[attr] = attr_value                              # Apply attribute value to the neighbor
                                                        # ... some implementations can apply compound attributes directly
    if attr in _compound:                               # Compound attributes have to be applied to route maps
      append_policy_attribute(ngb,attr,_compound[attr],attr_value)
    api.node_config(node,_config_name)                  # And remember that we have to do extra configuration

  return Found

'''
set_policy_name -- set the neighbor-specific prefix for the policy objects needed for that neighbor
'''
def set_policy_name(intf: Box, ngb: Box, policy_idx: int) -> None:
  vrf_pfx = f'vrf-{intf.vrf}-' if 'vrf' in intf else ''
  ngb._policy_name = f'{vrf_pfx}{ngb.name}-{policy_idx}'

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
    policy_idx = 0
    for (intf,ngb) in _bgp.intf_neighbors(ndata,select=['ebgp']):
      policy_idx += 1
      if apply_policy_attributes(ndata,ngb,intf,topology):  # If we applied at least some bgp.policy attribute to the neighbor
        set_policy_name(intf,ngb,policy_idx)                # ... set the per-neighbor policy name
