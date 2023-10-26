import typing
from box import Box
from netsim.utils import bgp as _bgp
from netsim import api,data

_config_name = 'bgp.policy'

_requires    = [ 'bgp' ]

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
  global _config_name,_direct,_compound,_attr_list
  _direct   = topology.defaults.bgp.attributes.p_attr.direct
  _compound = topology.defaults.bgp.attributes.p_attr.compound
  _attr_list = _direct + list(_compound.keys())

  for n, ndata in topology.nodes.items():
    if 'bgp' not in ndata.module:                           # Skip nodes not running BGP
      continue

    _bgp.cleanup_neighbor_attributes(ndata,topology,_attr_list)
    policy_idx = 0

    # Get _default_locpref feature flag (could be None), then figure out if we need to copy
    # node-level locpref to all EBGP neighbors. That test is a bit convolutaed to make
    # sure we don't get tripped up by None values
    #
    default_locpref = _bgp.get_device_bgp_feature('_default_locpref',ndata,topology)
    copy_locpref = False if default_locpref else 'locpref' in ndata.bgp

    # Now iterate over all EBGP neighbors (global and VRF) and apply bgp.policy interface
    # attributes to the neighbors
    #
    for (intf,ngb) in _bgp.intf_neighbors(ndata,select=['ebgp']):
      policy_idx += 1
      if copy_locpref and not intf.get('bgp.locpref',False):
        intf.bgp.locpref = ndata.bgp.locpref
      if apply_policy_attributes(ndata,ngb,intf,topology):  # If we applied at least some bgp.policy attribute to the neighbor
        set_policy_name(intf,ngb,policy_idx)                # ... set the per-neighbor policy name
