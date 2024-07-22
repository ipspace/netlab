#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing, re
import netaddr
from box import Box

from . import _Module,_routing,_dataplane,get_effective_module_attribute
from ..utils import log
from .. import data
from ..data import global_vars
from ..data.types import must_be_list
from ..augment import devices,groups,links,addressing

set_kw: typing.Optional[Box] = None
match_kw: typing.Optional[Box] = None

"""
normalize_routing_entry: generic normalization of any list used by the routing module
"""
def normalize_routing_entry(p_entry: Box, p_idx: int) -> Box:
  if 'action' not in p_entry:                               # Set the default action to 'permit' if missing
    p_entry.action = 'permit'

  if 'sequence' not in p_entry:                             # ... and the default sequence # to 10-times RP entry position
    p_entry.sequence = (p_idx + 1) * 10

  return p_entry

"""
policy_shortcut: convert shortcut attributes (ex: locpref) into normalized ones (ex: set.locpref)
"""
def policy_shortcut(p_entry: Box, p_kw: str, kw_set: Box) -> None:
  for k in kw_set:                                          # Iterate over shortcut keywords
    if k not in p_entry:                                    # ... not in this RP entry, move on
      continue

    p_entry[p_kw][k] = p_entry[k]                           # Move the keyword into target dictionary
    p_entry.pop(k,None)                                     # ... and remove it from RP entry or the validation will fail

"""
normalize_policy_entry:

* Eliminate shortcuts in routing policy entries
* Add default values of 'sequence' and 'action' parameters
"""
def normalize_policy_entry(p_entry: Box, p_idx: int) -> Box:
  global set_kw,match_kw

  if set_kw is None:                                        # Premature optimization: cache the SET keywords
    topology = global_vars.get_topology()
    if topology is None:
      return p_entry
    set_kw = topology.defaults.routing.attributes.route_map.set
    match_kw = topology.defaults.routing.attributes.route_map.match

  if set_kw:
    policy_shortcut(p_entry,'set',set_kw)

  if match_kw:
    policy_shortcut(p_entry,'match',match_kw)

  normalize_routing_entry(p_entry,p_idx)                    # Finally, do generic normalization

  return p_entry

"""
normalize_routing_object: Normalize global- or node routing object data

Please note that this function is called before the data has been validated, so we have to extra-careful
"""
def normalize_routing_object(o_list: list, callback: typing.Callable) -> None:
  for p_idx,p_entry in enumerate(o_list):         # Iterate over routing object entries and normalize them
    if not isinstance(o_list[p_idx],dict):        # Skip anything that is not a dictionary, validation will bark
      continue
      
    o_list[p_idx] = callback(o_list[p_idx],p_idx)

def normalize_routing_objects(
      o_dict: typing.Optional[Box],
      o_type: str,
      normalize_callback: typing.Callable,
      topo_object: bool = False) -> None:

  if o_dict is None:                                        # Nothing to do, I'm OK with that ;)
    return

  if not isinstance(o_dict,Box):                            # Object is not a box, let validation deal with that
    return

  for o_name in list(o_dict.keys()):                        # Iterate over the dictionary
    if o_dict[o_name] is None:                              # if the object value is None, it could be a placeholder
      if topo_object:
        log.error(
          f'Global routing {o_type} {o_name} cannot be None. Use an empty list if you want to have an empty object',
          category=log.IncorrectValue,
          module='routing')
      continue

    if isinstance(o_dict[o_name],Box):                      # Transform single-entry shortcut into a single-element list
      o_dict[o_name] = [ o_dict[o_name] ]

    if not isinstance(o_dict[o_name],list):                 # Still not a list? Let validation deal with that ;)
      continue

    normalize_routing_object(o_dict[o_name],normalize_callback)

"""
check_routing_object: validate that a device supports the requested routing object
"""
def check_routing_object(p_name: str,o_type: str, node: Box,topology: Box) -> bool:
  d_features = devices.get_device_features(node,topology.defaults)
  if not d_features.routing[o_type]:
    log.error(
      f"Device {node.device} (node {node.name}) does not support '{o_type}' objects ({p_name})",
      category=log.IncorrectAttr,
      module='routing')
    return False
  
  return True

"""
check_routing_policy: validate that all the device you want to use a route-map on
supports all the SET and MATCH keywords

Please note that this function is called after topology data validation, so we know
the attributes make sense.
"""
def check_routing_policy(p_name: str,o_type: str, node: Box,topology: Box) -> bool:
  p_data = node.get(f'routing.policy.{p_name}',None)        # Use this convoluted getter in case we get called out of context
  d_features = devices.get_device_features(node,topology.defaults)
  d_features = d_features.routing.policy                    # Get per-device routing policy features

  if not d_features:                                        # Sanity check: does the device support routing policy features?
    log.error(
      f'Device {node.device} (node {node.name}) does not support routing polices (policy {p_name})',
      category=log.IncorrectAttr,
      module='routing')
    return False

  OK = True
  for p_entry in p_data:                                    # Now iterate over routing policy entries
    for p_param in ('set','match'):                         # Check SET and MATCH parameters
      if p_param not in p_entry:                            # No parameters of this type, move on
        continue
      for kw in p_entry[p_param].keys():                    # Iterate over all SET/MATCH settings
        if kw not in d_features[p_param]:                   # if a setting is not supported by the device...
          OK = False                                        # ... remember we found an error
          log.error(                                        # ... and report it
            f"Device {node.device} (node {node.name}) does not support routing policy '{p_param}' keyword '{kw}' "+\
            f"used in {p_name} entry #{p_entry.sequence}",
            category=log.IncorrectType,
            module='routing')

  return OK                                                 # Return cumulative error status

"""
Import/merge a single global routing object into node routing object table

Return merged routing object or None if the node routing object has not been modified or does not exist
"""
def import_routing_object(pname: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  topo_pdata = topology.get(f'routing.{o_name}',{})

  # First check whether the node routing object is missing or set to None (no value)
  #
  if pname not in node.routing[o_name] or node.routing[o_name][pname] is None:
    if pname not in topo_pdata:                             # We know we need 'pname', so if it's not in the global policy table
      log.error(                                            # ... we have to throw an error
        f'Global routing {o_name} {pname} referenced in node {node.name} does not exist',
        category=log.MissingValue,
        module='routing')
      return None

    node.routing[o_name][pname] = topo_pdata[pname]         # Otherwise, copy global policy to node policy
    return node.routing[o_name][pname]                      # ... and return it because it might have to be validated

  # OK, we have an existing node routing policy
  if pname not in topo_pdata:                               # Is there anything to merge?
    return None                                             # Nope, exit

  np_data = node.routing[o_name][pname]                     # Prepare for merge: get node- and global entries
  tp_data = topo_pdata[pname]
  sqlist  = [ pe.sequence for pe in np_data ]               # Get the list of sequence numbers from the local policy

  # Now get global entries that are missing in the local policy,
  # add them to the local policy, and sort the result on sequence
  #
  tp_add  = [ pe for pe in tp_data if pe.sequence not in sqlist ]
  if not tp_add:                                            # Nothing to add, get out
    return None

  np_data = sorted(np_data + tp_add, key= lambda x: x.sequence)
  node.routing[o_name][pname] = np_data
  return np_data

"""
import_policy_filters: Import all routing filters (prefix lists, community lists, as-path lists...)
needed by the just-imported routing policy
"""
match_object_map: dict = {
  'prefix': 'prefix',                                       # Prefix match requires a 'prefix' object
  'nexthop': 'prefix'                                       # Next-hop match requires a 'prefix' object
}

def import_policy_filters(pname: str, o_name: str, node: Box, topology: Box) -> None:
  global match_object_map, normalize_dispatch, transform_dispatch

  for p_entry in node.routing.policy[pname]:                # Iterate over routing policy entries
    if not 'match' in p_entry:                              # No match condition, nothing to check
      continue
    for kw in match_object_map.keys():                      # Iterate over match keywords
      if kw in p_entry.match:                               # A filter is used in the route-map ==> import it
        r_object = match_object_map[kw]
        f_import = import_routing_object(p_entry.match[kw],r_object,node,topology)
        if f_import:                                        # If we imported any new data...
          if r_object in normalize_dispatch:                # ... normalize the filter entries
            normalize_routing_object(f_import,normalize_dispatch[r_object]['callback'])
          if r_object in transform_dispatch:                # ... and transform the filter into its final form
            transform_dispatch[r_object]['import'](p_entry.match[kw],r_object,node,topology)

"""
Import/merge a single global routing policy into node routing policy table

This function calls the generic import function and then tries to import all the global
objects required by the routing policy (for example, the prefix lists)
"""
def import_routing_policy(pname: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  p_import = import_routing_object(pname,o_name,node,topology)
  if p_import is None:
    return p_import
  
  import_policy_filters(pname,o_name,node,topology)
  return p_import

"""
Dispatch table for global-to-node object import
"""
import_dispatch: typing.Dict[str,dict] = {
  'policy': {
    'import' : import_routing_policy,
    'check'  : check_routing_policy,
    'related': import_policy_filters },
  'prefix': {
    'import' : import_routing_object,
    'check'  : check_routing_object }
}

"""
Import or merge global routing policies into node routing policies
"""
def process_routing_data(node: Box,o_type: str, topology: Box, dispatch: dict) -> None:
  if o_type not in dispatch:                         # pragma: no cover
    log.fatal(f'Invalid routing object {o_type} passed to process_routing_data')

  node_pdata = node.get(f'routing.{o_type}',None)
  if not isinstance(node_pdata,dict):
    return

  for p_name in list(node_pdata.keys()):
    if dispatch[o_type]['import'](p_name,o_type,node,topology) is not None:
      if 'check' in dispatch[o_type]:
        dispatch[o_type]['check'](p_name,o_type,node,topology)
    if 'related' in dispatch[o_type]:
      dispatch[o_type]['related'](p_name,o_type,node,topology)

"""
Dispatch table for data normalization
"""
normalize_dispatch: typing.Dict[str,dict] = {
  'policy':
    { 'namespace': 'routing.policy',
      'object'   : 'policy',
      'callback' : normalize_policy_entry },
  'prefix':
    { 'namespace': 'routing.prefix',
      'object'   : 'prefix filter',
      'callback' : normalize_routing_entry }
}

"""
normalize_routing_data: execute the normalization functions for all routing objects
"""
def normalize_routing_data(r_object: Box, topo_object: bool = False) -> None:
  global normalize_dispatch

  for dp in normalize_dispatch.values():
    normalize_routing_objects(
      o_dict=r_object.get(dp['namespace'],None),
      o_type=dp['object'],
      normalize_callback=dp['callback'],
      topo_object=topo_object)

"""
expand_prefix_entry: Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
"""
def expand_prefix_entry(p_entry: Box, topology: Box) -> Box:
  extra_data = None
  if 'pool' in p_entry:
    extra_data = topology.addressing[p_entry.pool]
    p_entry.pop('pool',None)

  if 'prefix' in p_entry:
    extra_data = topology.prefix[p_entry.prefix]
    p_entry.pop('prefix',None)

  if extra_data:
    for af in ('ipv4','ipv6'):
      if af in extra_data:
        p_entry[af] = extra_data[af]

  return p_entry

"""
adjust_pfx_min_max: Adjust prefix list entry min/max keywords
"""
def adjust_pfx_min_max(p_entry: Box, m_kw: str, af: str, p_name: str, node: Box) -> None:
  if m_kw not in p_entry:
    return

  if isinstance(p_entry[m_kw],dict):
    if af not in p_entry[m_kw]:
      return
    m_value = p_entry[m_kw][af]
  else:
    m_value = p_entry[m_kw]

  if m_value < 0:
    log.error(
      f'Prefix filter {m_kw} value should be >= 0 (policy {p_name}#{p_entry.sequence} on node {node.name})',
      category=log.IncorrectValue,
      module='routing')
    return

  m_max = 32 if af == 'ipv4' else 128
  if m_value > m_max:
    log.error(
      f'Prefix filter {af}.{m_kw} value should be <= {m_max} (policy {p_name}#{p_entry.sequence} on node {node.name})',
      category=log.IncorrectValue,
      module='routing')
    return

  p_entry[m_kw] = m_value

"""
create_af_entry: create AF-specific prefix-list entry
"""
def create_pfx_af_entry(p_entry: Box, af: str, p_name: str, node: Box) -> Box:
  af_p_entry = Box(p_entry)                                 # Create a copy of the current p_entry
  for af_x in ('ipv4','ipv6'):                              # ... remove all other address families
    if af_x in p_entry and af_x != af:
      af_p_entry.pop(af_x,None)

  for m_kw in ('min','max'):
    adjust_pfx_min_max(af_p_entry,m_kw,af,p_name,node)

  return af_p_entry

"""
create_empty_prefix_list: Create an empty per-AF prefix list
"""
def create_empty_prefix_list(af: str) -> list:
  p_entry = { 'sequence': 10, 'action': 'deny' }
  p_entry[af] = '0.0.0.0/0' if af == 'ipv4' else '::/0'
  return [ p_entry ]

"""
expand_prefix_list:

* Transform all entries in the prefix list
* Build IPv4 and IPv6 prefix lists
"""
def expand_prefix_list(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  for (p_idx,p_entry) in enumerate(node.routing[o_name][p_name]):
    node.routing[o_name][p_name][p_idx] = expand_prefix_entry(node.routing[o_name][p_name][p_idx],topology)

  af_prefix: dict = {}                                      # Prepare dictionary of per-AF prefix lists
  for af in ('ipv4','ipv6'):                                # Iterate over address families (sorry, no CLNS or IPX)
    af_prefix[af] = []                                      # Start with an emtpy per-AF list
    for p_entry in node.routing[o_name][p_name]:            # Iterate over prefix list entries
      if af in p_entry:                                     # Is the current AF in the prefix list entry?
        af_p_entry = create_pfx_af_entry(p_entry,af,p_name,node)
        af_prefix[af].append(af_p_entry)                    # create af-specific entry and append it to per-AF list

    if af_prefix[af]:                                       # Do we have a non-empty per-AF prefix list?
      node.routing['_'+o_name][af][p_name] = af_prefix[af]  # ... yes, save it
    else:
      node.routing['_'+o_name][af][p_name] = create_empty_prefix_list(af)      

  return None                                               # No need to do additional checks

"""
Dispatch table for post-transform processing. Currently used only to
expand the prefixes/pools in prefix list.
"""
transform_dispatch: typing.Dict[str,dict] = {
  'prefix': {
    'import': expand_prefix_list
  },
}

class Routing(_Module):

  def module_pre_default(self, topology: Box) -> None:
    topology.prefix = topology.defaults.prefix + topology.prefix
    normalize_routing_data(topology,topo_object=True)

  def node_pre_default(self, node: Box, topology: Box) -> None:
    normalize_routing_data(node)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global import_dispatch

    for o_name in import_dispatch.keys():
      process_routing_data(node,o_name,topology,import_dispatch)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    global transform_dispatch

    for o_name in transform_dispatch.keys():
      process_routing_data(node,o_name,topology,transform_dispatch)
