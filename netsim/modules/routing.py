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
normalize_policy_entry:

* Eliminate shortcuts in routing policy entries
* Add default values of 'sequence' and 'action' parameters
"""
def normalize_policy_entry(p_entry: Box, p_idx: int) -> Box:
  global set_kw

  if set_kw is None:                                        # Premature optimization: cache the SET keywords
    topology = global_vars.get_topology()
    if topology is None:
      return p_entry
    set_kw = topology.defaults.routing.attributes.route_map.set

  for k in set_kw:                                          # Now iterate over SET keywords that have shortcuts
    if k not in p_entry:                                    # ... not in this RP entry, move on
      continue

    p_entry.set[k] = p_entry[k]                             # Move the keyword into SET dictionary
    p_entry.pop(k,None)                                     # ... and remove it from RP entry or the validation will fail

  normalize_routing_entry(p_entry,p_idx)                    # Finally, do generic normalization

  return p_entry

"""
normalize_prefix_entry: expand 'pool' and 'prefix' arguments into IPv4/IPv6 prefixes
"""
def normalize_prefix_entry(p_entry: Box, p_idx: int) -> Box:
  global set_kw

  if set_kw is None:                                        # Premature optimization: cache the SET keywords
    topology = global_vars.get_topology()
    if topology is None:
      return p_entry
    set_kw = topology.defaults.routing.attributes.route_map.set

  for k in set_kw:                                          # Now iterate over SET keywords that have shortcuts
    if k not in p_entry:                                    # ... not in this RP entry, move on
      continue

    p_entry.set[k] = p_entry[k]                             # Move the keyword into SET dictionary
    p_entry.pop(k,None)                                     # ... and remove it from RP entry or the validation will fail

  normalize_routing_entry(p_entry,p_idx)                    # Finally, do generic normalization

  return p_entry

"""
normalize_routing_object: Normalize global- or node routing object data

Please note that this function is called before the data has been validated, so we have to extra-careful
"""
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

    for p_idx,p_entry in enumerate(o_dict[o_name]):         # Now iterate over routing object entries and normalize them
      if not isinstance(o_dict[o_name][p_idx],dict):        # Skip anything that is not a dictionary, validation will bark
        continue
      o_dict[o_name][p_idx] = normalize_callback(o_dict[o_name][p_idx],p_idx)

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
Import/merge a single global routing policy into node routing policy table

This function calls the generic import function and then tries to import all the global
objects required by the routing policy (for example, the prefix lists)
"""
def import_routing_policy(pname: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  return import_routing_object(pname,o_name,node,topology)

import_dispatch: typing.Dict[str,dict] = {
  'policy': {
    'import': import_routing_policy,
    'check' : check_routing_policy },
  'prefix': {
    'import': import_routing_object,
    'check' : check_routing_object }
}

"""
Import or merge global routing policies into node routing policies
"""
def import_routing_data(node: Box,o_type: str, topology: Box) -> None:
  global import_dispatch

  if o_type not in import_dispatch:                         # pragma: no cover
    log.fatal(f'Invalid routing object {o_type} passed to import_routing_data')

  node_pdata = node.get(f'routing.{o_type}',None)
  if not isinstance(node_pdata,dict):
    return

  for p_name in list(node_pdata.keys()):
    if import_dispatch[o_type]['import'](p_name,o_type,node,topology) is not None:
      import_dispatch[o_type]['check'](p_name,o_type,node,topology)

normalize_dispatch: typing.List[dict] = [
  { 'namespace': 'routing.policy',
    'object'   : 'policy',
    'callback' : normalize_policy_entry },
  { 'namespace': 'routing.prefix',
    'object'   : 'prefix filter',
    'callback' : normalize_routing_entry } ]

"""
normalize_routing_data: execute the normalization functions for all routing objects
"""
def normalize_routing_data(r_object: Box, topo_object: bool = False) -> None:
  global normalize_dispatch

  for dp in normalize_dispatch:
    normalize_routing_objects(
      o_dict=r_object.get(dp['namespace'],None),
      o_type=dp['object'],
      normalize_callback=dp['callback'],
      topo_object=topo_object)

class Routing(_Module):

  def module_pre_default(self, topology: Box) -> None:
    normalize_routing_data(topology,topo_object=True)

  def node_pre_default(self, node: Box, topology: Box) -> None:
    normalize_routing_data(node)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global import_dispatch

    for o_name in import_dispatch.keys():
      import_routing_data(node,o_name,topology)

