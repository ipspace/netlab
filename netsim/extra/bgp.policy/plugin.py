import typing

from box import Box

from netsim import api, data
from netsim.augment import devices
from netsim.data import types
from netsim.modules.routing.policy import check_routing_policy, import_routing_policy
from netsim.utils import log
from netsim.utils import routing as _bgp

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
    
  result = types.check_num_type(value,min_value,max_value)
  return expected_type if '_type' in result else result

types.register_type('autobw',must_be_autobw)

"""
copy_routing_attributes: copy select routing policy SET attributes into BGP node/link/interface attributes
to minimize data duplication
"""
def copy_routing_attributes(topology: Box) -> None:
  src_attr = topology.defaults.attributes.rp_entry.set      # Global routing policy entry definition
  dst_attr = topology.defaults.bgp.attributes               # Destination: BGP attributes
  ctrl_set = topology.defaults.bgp.attributes.p_attr        # Get the copy lists

  for ns in ('node','link','interface'):                    # Iterate over interesting namespaces
    for kw in ctrl_set.get(ns,[]):                          # ... and copy select routing policy attributes
      if kw in src_attr:                                    # ... assuming they exist
        dst_attr[ns][kw] = src_attr[kw]                     # ... into the target namespace of BGP attributes

"""
copy_device_features: copy device routing policy SET features to BGP features to the plugin to check
whether a BGP policy attribute can be applied directly to the BGP neighbor
"""
def copy_device_features(topology: Box) -> None:
  ctrl_set = topology.defaults.bgp.attributes.p_attr        # Get the copy lists
  for ddata in topology.defaults.devices.values():
    d_feat = ddata.features                                 # Get device features
    d_set  = d_feat.get('routing.policy.set',{})            # Get the POLICY SET capabilities for the routing module
    if not d_set:                                           # The device does not support the generic routing module, skip it
      continue
    for attr in ctrl_set.interface:                         # Iterate over interface-level bgp.policy attributes
      if attr in d_set:                                     # Is the attribute supported by device POLICY SET capabilities?
        if isinstance(d_set,Box):                           # If the POLICY SET is a dictionary...
          d_feat.bgp[attr] = d_set[attr]                    # ... copy value into device BGP features
        else:
          d_feat.bgp[attr] = True                           # ... otherwise just set it to TRUE

def init(topology: Box) -> None:
  data.append_to_list(topology,'_extra_module','routing')   # bgp.policy plugin needs routing policies (route maps)
  copy_routing_attributes(topology)
  copy_device_features(topology)

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
  _bgp.clear_bgp_session(node,ngb)

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
    if f'policy.{direction}' in ngb:                        # Do we also have configured bgp.policy? Time for an error
      attr_policy = ngb._policy[direction][0]               # First collect the attribute-generated policy
      p_attr = ','.join(attr_policy.set.keys())             # ... and gather attributes from it

      # Special case: the error might be caused by node-wide locpref copied to interfaces
      #
      if p_attr == 'locpref' and ndata.get('bgp.locpref',None) == attr_policy.set.locpref:
        p_attr += ' (possibly node-wide)'

      # Now we know what's wrong and can provide more data together with the error message
      #
      more_data = [ f'Policy({direction}): {ngb.policy[direction]}, attributes: {p_attr}' ]
      log.error(
        f'Cannot mix bgp.policy with individual BGP policy attributes -- node {ndata.name} neighbor {ngb.name}',
        category=log.IncorrectValue,
        more_data = more_data,
        module='bgp.policy')
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

    # Get the routing policy name, try to import it, and check it if the import was successful
    #
    pname = intf.bgp.policy[direction]
    if import_routing_policy(pname,'policy',ndata,topology):
      if not check_routing_policy(pname,'policy',ndata,topology):
        continue                                            # Skip the rest if the policy validation failed

    ngb.policy[direction] = intf.bgp.policy[direction]      # Copy interface BGP routing policy into a neighbor
    apply_config(ndata,ngb)                                 # Remember that we have to do extra configuration

'''
Process routing aggregation requests:

* Check the feature support
* Import routing policies needed for route aggregation
'''
def route_aggregation(ndata: Box, topology: Box) -> None:
  global _config_name
  for (bdata,_,vname) in _bgp.rp_data(ndata,'bgp'):         # Iterate over global and VRF BGP instances
    if 'aggregate' not in bdata:                            # This instance is not doing aggregation
      continue
    api.node_config(ndata,_config_name)                     # Remember that we have to do extra configuration
    bpath = f'nodes.{ndata.name}' + (f'.vrfs.{vname}' if vname else '')
    for a_idx,a_entry in enumerate(bdata.aggregate):        # Now check every aggregation entry
      stat = devices.check_optional_features(               # ... for optional features that
                data=a_entry,                               # ... might not be supported by this device
                path=bpath+f'.aggregate[{a_idx}]',
                node=ndata,
                topology=topology,
                attribute='bgp.aggregate',
                check_mode=devices.FC_MODE.BLACKLIST)
      if stat == devices.FC_MODE.ERR_ATTR:
        break
      for policy_kw in ['suppress_policy','attributes']:    # Finally, two attributes use routing policies
        if policy_kw in a_entry:                            # ... so if they are present
          pname = a_entry[policy_kw]                        # ... we need to import routing policies
          if import_routing_policy(pname,'policy',ndata,topology):
            check_routing_policy(pname,'policy',ndata,topology)

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

    route_aggregation(ndata,topology)
    _bgp.cleanup_neighbor_attributes(ndata,topology,_attr_list + [ 'policy' ])
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
