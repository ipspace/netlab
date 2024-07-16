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

  if 'action' not in p_entry:                               # Finally, set the default action to 'permit'
    p_entry.action = 'permit'

  if 'sequence' not in p_entry:                             # ... and the default sequence # to 10-times RP entry position
    p_entry.sequence = (p_idx + 1) * 10

  return p_entry

"""
normalize_routing_policies: Normalize global- or node routing policy data

Please note that this function is called before the data has been validated, so we have to extra-careful
"""
def normalize_routing_policies(pdata: typing.Optional[Box], topo_policy: bool = False) -> None:
  if pdata is None:                                         # Nothing to do, I'm OK with that ;)
    return

  for pname in list(pdata.keys()):                          # Iterate over the routing.policy dictionary
    if pdata[pname] is None:                                # if the policy value is None, it could be a placeholder
      if topo_policy:
        log.error(
          f'Global routing policy {pname} cannot be None. Use an empty list if you want to have an empty route-map',
          category=log.IncorrectValue,
          module='routing')
      continue

    if isinstance(pdata[pname],Box):                        # Transform single-entry shortcut into a single-element list
      pdata[pname] = [ pdata[pname] ]

    if not isinstance(pdata[pname],list):                   # Still not a list? Let validation deal with that ;)
      continue

    for p_idx,p_entry in enumerate(pdata[pname]):           # Now iterate over routing policy entries and normalize them
      if not isinstance(pdata[pname][p_idx],dict):          # Skip anything that is not a dictionary, validation will bark
        continue
      pdata[pname][p_idx] = normalize_policy_entry(pdata[pname][p_idx],p_idx)

"""
check_routing_policy: validate that all the device you want to use a route-map on
supports all the SET and MATCH keywords

Please note that this function is called after topology data validation, so we know
the attributes make sense.
"""
def check_routing_policy(p_name: str,node: Box,topology: Box) -> bool:
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
Import/merge a single global routing policy into node routing policy table

Return merged routing policy or None if the routing policy has not been modified or does not exist
"""
def import_routing_policy(pname: str,node: Box,topology: Box) -> typing.Optional[list]:
  topo_pdata = topology.get('routing.policy',{})

  # First check whether the node routing policy is missing or set to None (no value)
  #
  if pname not in node.routing.policy or node.routing.policy[pname] is None:
    if pname not in topo_pdata:                             # We know we need 'pname', so if it's not in the global policy table
      log.error(                                            # ... we have to throw an error
        f'Global routing policy {pname} referenced in node {node.name} does not exist',
        category=log.MissingValue,
        module='routing')
      return None

    node.routing.policy[pname] = topo_pdata[pname]          # Otherwise, copy global policy to node policy
    return node.routing.policy[pname]                       # ... and return it because it might have to be validated

  # OK, we have an existing node routing policy
  if pname not in topo_pdata:                               # Is there anything to merge?
    return None                                             # Nope, exit

  np_data = node.routing.policy[pname]                      # Prepare for merge: get node- and global entries
  tp_data = topo_pdata[pname]
  sqlist  = [ pe.sequence for pe in np_data ]               # Get the list of sequence numbers from the local policy

  # Now get global entries that are missing in the local policy,
  # add them to the local policy, and sort the result on sequence
  #
  tp_add  = [ pe for pe in tp_data if pe.sequence not in sqlist ]
  if not tp_add:                                            # Nothing to add, get out
    return None

  np_data = sorted(np_data + tp_add, key= lambda x: x.sequence)
  node.routing.policy[pname] = np_data
  return np_data

"""
Import or merge global routing policies into node routing policies
"""
def import_routing_policies(node: Box,topology: Box) -> None:
  node_pdata = node.get('routing.policy',None)
  if node_pdata is None:
    return

  for p_name in list(node_pdata.keys()):
    if import_routing_policy(p_name,node,topology) is not None:
      check_routing_policy(p_name,node,topology)

class Routing(_Module):

  def module_pre_default(self, topology: Box) -> None:
    normalize_routing_policies(topology.get('routing.policy',None),topo_policy=True)

  def node_pre_default(self, node: Box, topology: Box) -> None:
    normalize_routing_policies(node.get('routing.policy',None))

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    import_routing_policies(node,topology)

