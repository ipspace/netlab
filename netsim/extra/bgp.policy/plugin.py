import typing
from box import Box
from netsim.utils import bgp as _bgp, log
from netsim import api,data
from netsim.data import types
from netsim.modules.routing import import_routing_policy,check_routing_policy

_config_name = 'bgp.policy'

_requires    = [ 'bgp' ]

@types.type_test()
def must_be_autobw(
      value: typing.Any,
      min_value:  typing.Optional[int] = None,          # Minimum value
      max_value:  typing.Optional[int] = None,          # Maximum value
                ) -> dict:
  
  expected_type = { '_type': 'auto-bandwidth (an integer or keyword "auto")' }

  if isinstance(value,str):
    if value == 'auto':
      return { '_valid': True } 
    
  result = types.check_int_type(value,min_value,max_value)
  return expected_type if '_type' in result else result

types.register_type('autobw',must_be_autobw)

def init(topology: Box) -> None:
  data.append_to_list(topology,'_extra_module','routing')   # bgp.policy plugin needs routing policies (route maps)

'''
append_policy_attribute

* Apply a standalone policy attribute to an input or output policy
* If the policy does not exist, create a single-entry placeholder policy

The plugin does not support direct definition of BGP policies yet, but we're
trying to guess what the data structure should be to minimize the impact on
configuration templates
'''

def append_policy_attribute(ngb: Box, attr: str, direction: str, attr_value: typing.Any) -> None:
  if direction == 'both':                               # Some attributes could be applied in both directions
    for bidir in ('in','out'):                          # ... in which case check for 'in' and 'out' values in the attribute
      if bidir in attr_value:                           # ... and if the directional value is set, apply it
        append_policy_attribute(ngb,attr,bidir,attr_value[bidir])
    return                                              # ... then get out of here, recursive calls got the job done

  # Simple case: single direction (in or out)
  #
  if not ngb._policy[direction]:                        # Create an empty policy list if needed
    ngb._policy[direction] = [ data.get_empty_box() ]

  p_entry = ngb._policy[direction][0]                   # Modify first route map entry
  p_entry.set[attr] = attr_value                        # Set attribute
  p_entry.sequence = 10                                 # Make sure we have a sequence number
  p_entry.action = 'permit'                             # ... and an action

_attr_list: list = []
_direct: list = []
_compound: dict = {}

'''
Check whether the specified attribute can be applied in the requested direction. For example,
bgp.bandwidth does not work on outbound updates on Cisco IOSv
'''

_attr_error: Box = data.get_empty_box()

def check_attribute_direction(ndata: Box, ngb: Box, topology: Box, attr: str, attr_value: typing.Any) -> None:
  global _config_name,_attr_error

  if not isinstance(attr_value,dict):                   # Attribute value does not have in/out values, nothing to check
    return

  a_feature = _bgp.get_device_bgp_feature(attr,ndata,topology)
  if not isinstance(a_feature,dict):                    # Device has no restrictions, nothing to check
    return

  for kw in attr_value.keys():
    if kw not in a_feature:                             # Does the device support the specified keyword?
      if _attr_error[ndata.name][attr][kw]:             # Skip multiple errors
        continue                                        # ... display a single 'wrong key' error per node

      _attr_error[ndata.name][attr][kw] = { 'attr': True }

      log.error(
        f'You cannot use bgp.{attr}.{kw} on {ndata.device} (node {ndata.name})',
        category=log.IncorrectType,
        module=_config_name)
      continue

    if isinstance(a_feature[kw],bool):                  # Does the device have any further restrictions?
      continue

    if not isinstance(a_feature[kw],list):
      a_feature[kw] = [ a_feature[kw] ]

    if type(attr_value[kw]).__name__ in a_feature[kw] or attr_value[kw] in a_feature[kw]:
      continue                                          # The value matches expected type or value

    # Skip multiple errors (otherwise we would display one per neighbor)
    # Display at most one error per value per node
    #
    if _attr_error[ndata.name][attr][kw][attr_value[kw]]:
      continue

    _attr_error[ndata.name][attr][kw][attr_value[kw]] = True

    log.error(
      f'bgp.{attr}.{kw} should be {",".join(a_feature[kw])} on device {ndata.device} (node {ndata.name})' + \
      f' found "{attr_value[kw]}"',
      category=log.IncorrectType,
      module=_config_name)

'''
apply_config: add a plugin configuration template, collect BGP sessions that have to be cleared
'''
def apply_config(node: Box, ngb: Box) -> None:
  global _config_name
  api.node_config(node,_config_name)                    # Remember that we have to do extra configuration
  for af in ('ipv4','ipv6'):                            # ... and add sessions that have to be cleared
    if af in ngb:
      data.append_to_list(node.bgp,'_session_clear',ngb[af])

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
      check_attribute_direction(node,ngb,topology,attr,attr_value)
      append_policy_attribute(ngb,attr,_compound[attr],attr_value)

    apply_config(node,ngb)                              # Remember that we have to do extra configuration

  return Found

'''
fix_bgp_bandwidth: transform the bandwidth-as-int shortcut into bandwidth.in: int
'''

def fix_bgp_bandwidth(intf: Box) -> None:
  bw = intf.get('bgp.bandwidth',None)
  if bw is None:
    return
  
  if not isinstance(bw,dict):
    intf.bgp.bandwidth = { 'in': bw }

'''
bgp_policy_name -- get the neighbor-specific route map prefix
'''
def bgp_policy_name(intf: Box, ngb: Box, policy_idx: int) -> str:
  vrf_pfx = f'vrf-{intf.vrf}-' if 'vrf' in intf else ''
  return f'{vrf_pfx}{ngb.name}-{policy_idx}'

'''
create_routing_policy: create route maps needed for BGP neighbor policies
'''
def create_routing_policy(ndata: Box, ngb: Box, p_name: str) -> None:
  for direction in ['in','out']:                            # Check in- and out- route maps
    if f'_policy.{direction}' not in ngb:                   # Do we have bgp.policy-generated route map?
      continue
    if f'policy.{direction}' in ngb:                        # Do we also have configured bgp.policy?
      log.error(                                            # OOPS, can't have both
        f'Cannot mix in/out routing policies with individual bgp.policy attributes -- node {ndata.name} neighbor {ngb.name}',
        category=log.IncorrectValue,
        module='bgp.policy')
      print(ngb)
      continue

    data.append_to_list(ndata,'module','routing')
    rm_name = f'bp-{p_name}-{direction}'                    # Get the route-map name
    ndata.routing.policy[rm_name] = ngb._policy[direction]  # Copy neighbor routing policy to node routing policies
    ngb.policy[direction] = rm_name                         # And add a pointer to bgp.policy dictionary

  ngb.pop('_policy',None)                                   # Finally, clean up the temporary data structure

'''
apply_bgp_routing_policy: import and check the routing policies required by the bgp.policy attributes
'''
def apply_bgp_routing_policy(ndata: Box,ngb: Box,intf: Box,topology: Box) -> None:
  for direction in ['in','out']:                            # Check in- and outbound policies
    if f'bgp.policy.{direction}' not in intf:               # No policies applied in this direction, move on
      continue

    if 'routing' not in ndata.module:
      log.error(
        f"You cannot use 'bgp.policy' interface attribute on a node that does not use 'routing' module",
        category=log.IncorrectType,
        module='bgp.policy')
      return

    pname = intf.bgp.policy[direction]                      # Get the routing policy name
    if import_routing_policy(pname,ndata,topology):         # If we imported a routing policy
      if not check_routing_policy(pname,ndata,topology):    # Check whether it's valid
        continue                                            # ... and skip it if it's not

    ngb.policy[direction] = intf.bgp.policy[direction]      # Copy interface BGP routing policy into a neighbor
    apply_config(ndata,ngb)                                 # Remember that we have to do extra configuration

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
    # node-level locpref to all EBGP neighbors. That test is a bit convoluted to make
    # sure we don't get tripped up by None values
    #
    default_locpref = _bgp.get_device_bgp_feature('_default_locpref',ndata,topology)
    copy_locpref = False if default_locpref else 'locpref' in ndata.bgp

    # Now iterate over all EBGP neighbors (global and VRF) and apply bgp.policy interface
    # attributes to the neighbors
    #
    for (intf,ngb) in _bgp.intf_neighbors(ndata,select=['ebgp']):
      policy_idx += 1
      bgp_bandwidth = intf.get('bgp.bandwidth',False)
      if bgp_bandwidth:
        fix_bgp_bandwidth(intf)
        ndata.bgp._bandwidth = True
        if isinstance(bgp_bandwidth,dict) and 'out' in bgp_bandwidth:
          communities = ndata.get("bgp.community.ebgp",[])  # Get a reference to the ebgp communities
          if 'extended' not in communities:                 # Enable extended communities if not already
            communities.append('extended')
      if copy_locpref and not intf.get('bgp.locpref',False):
        intf.bgp.locpref = ndata.bgp.locpref
      if intf.get('bgp.policy',{}):
        apply_bgp_routing_policy(ndata,ngb,intf,topology)
      if apply_policy_attributes(ndata,ngb,intf,topology):  # If we applied at least some bgp.policy attribute to the neighbor
        p_name = bgp_policy_name(intf,ngb,policy_idx)       # Get the routing policy name
        create_routing_policy(ndata,ngb,p_name)             # and try to create the route map
