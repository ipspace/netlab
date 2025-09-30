#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing

from box import Box, BoxList

from ...augment import devices
from ...data import global_vars
from ...utils import log
from . import clist
from .normalize import (
  import_routing_object,
  normalize_routing_entry,
  normalize_routing_object,
)

set_kw: typing.Optional[Box] = None
match_kw: typing.Optional[Box] = None

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
def normalize_policy_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
  global set_kw,match_kw

  if not isinstance(p_entry,Box):                 # Skip anything that is not a box, validation will bark
    return p_entry

  if set_kw is None:                              # Premature optimization: cache the SET keywords
    topology = global_vars.get_topology()
    if topology is None:
      return p_entry
    set_kw = topology.defaults.routing.attributes.route_map.set
    match_kw = topology.defaults.routing.attributes.route_map.match

  if set_kw:                                      # Normalize set keywords
    policy_shortcut(p_entry,'set',set_kw)

  if match_kw:                                    # Normalize match keywords
    policy_shortcut(p_entry,'match',match_kw)

  prepend = p_entry.get('set.prepend',None)       # Normalize AS path prepending SET entry
  if prepend is not None and isinstance(prepend,(int,str)):
    p_entry.set.prepend = { 'path': str(prepend) }

  normalize_routing_entry(p_entry,p_idx)          # Finally, do generic normalization

  return p_entry

"""
is_kw_supported: Check whether a keyword is supported according to device features

It should be an easy test; what complicates it is our flexibility:

* The features could be specified as a list or a dict
* The dict values could be set to False (meaning DOES NOT WORK)
"""
def is_kw_supported(kw: str, kw_data: typing.Union[Box,BoxList]) -> bool:
  if kw not in kw_data:
    return False
  
  if isinstance(kw_data,Box) and not kw_data.get(kw,False):
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
        if not is_kw_supported(kw,d_features[p_param]):     # if a setting is not supported by the device...
          OK = False                                        # ... remember we found an error
          log.error(                                        # ... and report it
            f"Device {node.device} (node {node.name}) does not support routing policy '{p_param}' keyword '{kw}' "+\
            f"used in {p_name} entry #{p_entry.sequence}",
            category=log.IncorrectType,
            module='routing')
          continue
        if not isinstance(d_features[p_param],Box):         # No further work needed
          continue
        kw_data = d_features[p_param][kw]                   # Get keyword-specific data
        if not isinstance(kw_data,Box):                     # Keyword-specific data is not a dictionary
          continue                                          # ... no further checks are necessary
        if not isinstance(p_entry[p_param][kw],Box):        # The value is not a dictionary
          continue                                          # ... let validation deal with that
        for kw_opt in p_entry[p_param][kw].keys():          # Now iterate over the suboptions
          if kw_data.get(kw_opt,False):                     # ... and if they're in the device features
            continue                                        # ... we're good to go
          log.error(                                        # Otherwise report an error
            f"Device {node.device} (node {node.name}) does not support routing policy '{p_param}'"+\
            f" keyword '{kw}.{kw_opt}' used in {p_name} entry #{p_entry.sequence}",
            category=log.IncorrectType,
            module='routing')
          OK = False

  return OK                                                 # Return cumulative error status

"""
import_policy_filters: Import all routing filters (prefix lists, community lists, as-path lists...)
needed by the just-imported routing policy
"""
match_object_map: dict = {
  'match.prefix': 'prefix',                                 # Prefix match requires a 'prefix' object
  'match.nexthop': 'prefix',                                # Next-hop match requires a 'prefix' object
  'match.aspath': 'aspath',                                 # AS path match requires an 'aspath' object
  'match.community': 'community',                           # Community match requires a 'community' object
  'set.community.delete_list': 'community'                  # Community delete_list requires a 'community' object
}

def import_policy_filters(pname: str, o_name: str, node: Box, topology: Box) -> None:
  from . import import_dispatch, normalize_dispatch, transform_dispatch

  global match_object_map

  for p_entry in node.routing.policy[pname]:                # Iterate over routing policy entries
    for kw in match_object_map.keys():                      # Iterate over match keywords
      if kw in p_entry:                                     # A filter is used in the route-map ==> import it
        r_object = match_object_map[kw]
        f_import = import_routing_object(p_entry[kw],r_object,node,topology)
        if f_import:                                        # If we imported any new data...
          if r_object in normalize_dispatch:                # ... normalize the filter entries
            normalize_routing_object(f_import,normalize_dispatch[r_object]['callback'])
          if r_object in import_dispatch and 'check' in import_dispatch[r_object]:
            import_dispatch[r_object]['check'](p_entry[kw],r_object,node,topology)
          if r_object in transform_dispatch:                # ... and transform the filter into its final form
            transform_dispatch[r_object]['import'](p_entry[kw],r_object,node,topology)

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
adjust_routing_policy: Make routing policy adjustments

  * Replace 'set.community.delete' with 'set.community.delete_list' for devices that don't support
    the 'set community delete' configuration command
"""
def adjust_routing_policy(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  for (_,p_entry) in enumerate(node.routing[o_name][p_name]):
    clist.replace_community_delete(node,p_name,p_entry,topology)
  
  return None
