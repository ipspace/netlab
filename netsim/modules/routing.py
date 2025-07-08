#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing, re
import ipaddress
from box import Box,BoxList

from . import _Module,_routing,_dataplane,get_effective_module_attribute
from ..utils import log, routing as _rp_utils
from .. import data
from ..data import global_vars,get_box
from ..data.types import must_be_list
from ..augment import devices,groups,links,addressing

set_kw: typing.Optional[Box] = None
match_kw: typing.Optional[Box] = None

"""
normalize_routing_entry: generic normalization of any list used by the routing module
"""
def normalize_routing_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
  if not isinstance(p_entry,Box):                 # Skip anything that is not a box, validation will bark
    return p_entry

  if 'action' not in p_entry:                     # Set the default action to 'permit' if missing
    p_entry.action = 'permit'

  if 'sequence' not in p_entry:                   # ... and the default sequence # to 10-times RP entry position
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
normalize_aspath_entry: turn non-dictionary entries into dictionaries with 'path' attribute
"""
def normalize_aspath_entry(p_entry: typing.Any, p_idx: int) -> Box:
  if not isinstance(p_entry,Box):
    p_entry = get_box({ 'path': p_entry })

  if 'path' not in p_entry and 'list' not in p_entry and 'regexp' not in p_entry:
    p_entry.path = '.*'

  if 'path' in p_entry:
    if isinstance(p_entry.path,list):
      p_list = [ str(p) for p in p_entry.path ]
      p_entry.path = ' '.join(p_list)

  normalize_routing_entry(p_entry,p_idx)
  return p_entry

"""
normalize_routing_object: Normalize global- or node routing object data

Please note that this function is called before the data has been validated, so we have to extra-careful
"""
def normalize_routing_object(o_list: list, callback: typing.Callable) -> None:
  for p_idx,p_entry in enumerate(o_list):         # Iterate over routing object entries and normalize them
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

    if not isinstance(o_dict[o_name],list):                 # Object not a list? Let's make it one ;)
      o_dict[o_name] = [ o_dict[o_name] ]

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
  'match.prefix': 'prefix',                                 # Prefix match requires a 'prefix' object
  'match.nexthop': 'prefix',                                # Next-hop match requires a 'prefix' object
  'match.aspath': 'aspath',                                 # AS path match requires an 'aspath' object
  'match.community': 'community',                           # Community match requires a 'community' object
  'set.community.delete_list': 'community'                  # Community delete_list requires a 'community' object
}

def import_policy_filters(pname: str, o_name: str, node: Box, topology: Box) -> None:
  global match_object_map, normalize_dispatch, transform_dispatch, import_dispatch

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
import_community_list -- has to check whether the target clist was already fixed, which means
the transform_dispatch has already been called
"""
def import_community_list(pname: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  clist = node.get(f'routing.{o_name}.{pname}',None)
  if isinstance(clist,Box):
    return None

  return import_routing_object(pname,o_name,node,topology)

"""
include_global_static_routes: Include global static routes into node static routes
"""
def include_global_static_routes(o_data: BoxList,o_type: str,node: Box,topology: Box) -> typing.Optional[BoxList]:
  if not isinstance(o_data,list):
    return None

  include_limit = 20
  sr_name = f'Static route list in node {node.name}'

  while True:
    include_rq = False
    for idx in range(len(o_data)):
      sr_data = o_data[idx]
      if 'include' not in sr_data:
        continue

      if sr_data.include not in topology.get('routing.static',{}):
        log.error(
          f'{sr_name} is trying to include non-existent global static route list {sr_data.include}',
          category=log.MissingValue,
          module='routing')
        sr_data.remove = True
        continue

      include_rq = True
      inc_data = topology.routing.static[sr_data.include]
      for sr_entry in inc_data:        
        if 'nexthop' in sr_data:
          sr_entry = sr_entry + { 'nexthop': sr_data.nexthop }
        o_data.append(sr_entry)

      sr_data.remove = True

    if not include_rq:
      return o_data

    o_data = BoxList([ sr_data for sr_data in o_data if not sr_data.get('remove',False) ])
    include_limit -= 1
    if not include_limit:
      log.error(
        f'{sr_name} has exceeded the include depth limit',
        more_hints='You might have a loop of "include" requests',
        category=log.IncorrectValue,
        module='routing')
      return o_data

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
    'check'  : check_routing_object },
  'aspath': {
    'import' : import_routing_object,
    'check'  : check_routing_object },
  'community': {
    'import' : import_community_list,
    'check'  : check_routing_object },
  'static': {
    'start'  : include_global_static_routes
  }
}

"""
Import or merge global routing policies into node routing policies
"""
def process_routing_data(node: Box,o_type: str, topology: Box, dispatch: dict, always_check: bool = True) -> None:

  def call_dispatch(p_name: typing.Union[str,int]) -> None:
    if 'import' in dispatch[o_type]:
      o_import = dispatch[o_type]['import'](p_name,o_type,node,topology)
    else:
      o_import = None
    if o_import is not None or always_check:
      if 'check' in dispatch[o_type]:
        dispatch[o_type]['check'](p_name,o_type,node,topology)
    if 'related' in dispatch[o_type]:
      dispatch[o_type]['related'](p_name,o_type,node,topology)

  if o_type not in dispatch:                         # pragma: no cover
    log.fatal(f'Invalid routing object {o_type} passed to process_routing_data')

  node_pdata = node.get(f'routing.{o_type}',None)
  if node_pdata is None:
    return

  if 'start' in dispatch[o_type]:
    result = dispatch[o_type]['start'](node_pdata,o_type,node,topology)
    if result is not None:
      node.routing[o_type] = result
      node_pdata = result

  if isinstance(node_pdata,dict):
    for p_name in list(node_pdata.keys()):
      call_dispatch(p_name)
  elif isinstance(node_pdata,list):
    for idx in range(len(node_pdata)):
      call_dispatch(idx)

  if 'cleanup' in dispatch[o_type]:
    result = dispatch[o_type]['cleanup'](node_pdata,o_type,node,topology)

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
      'callback' : normalize_routing_entry },
  'aspath':
    { 'namespace': 'routing.aspath',
      'object'   : 'AS path filter',
      'callback' : normalize_aspath_entry },
  'community':
    { 'namespace': 'routing.community',
      'object'   : 'BGP community filter',
      'callback' : normalize_aspath_entry },
}

"""
normalize_routing_data: execute the normalization functions for all routing objects
"""
def normalize_routing_data(r_object: Box, topo_object: bool = False, o_name: str = 'topology') -> None:
  global normalize_dispatch

  try:
    for dp in normalize_dispatch.values():
      if 'transform' in dp:
        if dp['namespace'] in r_object:
          xform = r_object[dp['namespace']]
          xform = dp['transform'](xform,o_type=dp['object'],topo_object=topo_object,o_name=o_name)
          if xform is not None:
            r_object[dp['namespace']] = xform
      elif 'callback' in dp:
        normalize_routing_objects(
          o_dict=r_object.get(dp['namespace'],None),
          o_type=dp['object'],
          normalize_callback=dp['callback'],
          topo_object=topo_object)
  except Exception as ex:
    log.warning(
      text=f"Cannot normalize {o_name} routing objects",
      more_data=str(ex),
      more_hints="Check further error messages for more details",
      module='routing')

"""
replace_community_delete:

* replace 'delete: true' with 'delete_list' if the 'set.community.delete' feature is set to 'clist'
* create a new community list if needed
"""
def replace_community_delete(node: Box, p_name: str, p_entry: Box, topology: Box) -> None:
  if not p_entry.get('set.community.delete',False):
    return
  features = devices.get_device_features(node,topology.defaults)
  if features.get('routing.policy.set.community.delete') != 'clist':
    return

  clist = []
  for type in ['standard','large','extended']:
    if type not in p_entry.set.community:
      continue
    elif type in ['large','extended']:
      log.error(
        f'Node {node.name} (device {node.device}) cannot delete {type} BGP communities in a routing policy',
        more_data=f'Policy {p_name} sequence# {p_entry.sequence}',
        category=log.IncorrectType,
        module='routing')
    else:
      clist += [ { 'type': 'standard', 'action': 'permit', '_value': i } for i in p_entry.set.community[type] ]

  if clist:
    cname = f"DEL_{p_name}_{p_entry.sequence}"
    node.routing.community[cname] = { 'action': 'permit', 'type': 'standard', 'value': clist }
    p_entry.set.community.delete_list = cname
  
  for kw in ['standard','large','extended','delete']:
    p_entry.set.community.pop(kw, None)

"""
adjust_routing_policy: Make routing policy adjustments

  * Replace 'set.community.delete' with 'set.community.delete_list' for devices that don't support
    the 'set community delete' configuration command
"""
def adjust_routing_policy(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  for (p_idx,p_entry) in enumerate(node.routing[o_name][p_name]):
    replace_community_delete(node,p_name,p_entry,topology)
  
  return None

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

def number_aspath_acl(p_name: str,o_name: str,node: Box,topology: Box) -> None:
  numacl = node.routing._numobj[o_name]
  if p_name not in numacl:
    maxacl = max([ 0 ] + [ acl for acl in numacl.values() ])
    numacl[p_name] = maxacl + 1

"""
fix_clist_entry: Fix an entry in the BGP community list.

When done, the entry will have:

* _value  -- set to whatever value user specified in regexp, list, or (internal) path attribute
* _regexp -- set if the value is a regular expression
"""
class MissingQuotes(Exception):
  pass

def fix_clist_entry(e_clist: Box, topology: Box) -> None:
  if 'regexp' in e_clist:                                   # Do we know we have a regexp?
    e_clist._value = e_clist.regexp                         # Copy regular expression into a common variable
    return

  value = e_clist.get('list','') or e_clist.get('path','')  # Get community value(s)
  int_list = [ v for v in value if isinstance(v,int) ]
  if int_list:
    raise MissingQuotes()

  if isinstance(value,list):                                # Convert list to a string of
    value = ' '.join([str(v) for v in value])               # ... space-separated values
  e_clist._value = value
  if not value:                                             # None specified? We have to do a wildcard match
    e_clist._value = '.*'
    e_clist.regexp = e_clist._value
  else:
    if not re.match('^[0-9: ]+$',value):                    # Is the value a simple community list expression?
      e_clist.regexp = e_clist._value

  for kw in ('path','list'):                                # Finally, clean up the now-unnecessary attributes
    e_clist.pop(kw,None)

"""
expand_community_list: transform BGP community lists into a dictionary that indicates
whether they use regular expressions or not
"""
def expand_community_list(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  p_clist = node.routing[o_name][p_name]                    # Shortcut pointer to current community list
  if isinstance(p_clist,Box) and 'value' in p_clist:        # Have we already transformed this clist?
    return None

  node.routing[o_name][p_name] = {                          # Move the permit/deny list into 'value
    'value': p_clist
  }

  p_clist = node.routing[o_name][p_name]                    # ... and fetch the new shortcut pointer
  regexp = False                                            # Figure out whether we need expanded clist
  for (p_idx,p_entry) in enumerate(p_clist.value):
    try:
      fix_clist_entry(p_clist.value[p_idx],topology)
    except MissingQuotes:
      log.error(
        f'BGP community list {p_name} line {p_idx+1} contains an integer',
        more_hints='You probably forgot to put an A:B value within quotes and YAML parser got confused',
        category=log.IncorrectValue,
        module='routing')
    regexp = regexp or bool(p_clist.value[p_idx].get('regexp',False))

  p_clist.type = 'expanded' if regexp else 'standard'       # Set clist type for devices that use standard/expanded
  p_clist.regexp = 'regexp' if regexp else ''               # And regexp flag for devices that use something else

  return None                                               # Message to caller: no need to do additional checks

"""
Extract just the AF information (host or prefix) from a data object

Returns a box with ipv4 and/or ipv6 components, either as prefixes (default)
or host addresses (when keep_prefix = false)
"""
def extract_af_info(addr: Box, keep_prefix: bool = True) -> Box:
  result = data.get_empty_box()
  for af in log.AF_LIST:                      # Iterate over address families
    if af not in addr:                        # AF not present, move on
      continue
    if isinstance(addr[af],bool):
      result[af] = addr[af]
    elif keep_prefix:                         # Do we need a prefix?
      result[af] = _rp_utils.get_prefix(addr[af])
    else:                                     # We need just the host part
      result[af] = _rp_utils.get_intf_address(addr[af])

  return result

"""
Get a string identifier for a static route

* Ideally, we'd have IPv4 and/or IPv6 prefixes
* Failing that, we could identify a static route based on its node, prefix, pool or include attributes
* Last resort: maybe we have at least the nexthop info
* Return 'null' if everything else fails :(
"""
def get_static_route_id(sr_data: Box) -> str:
  af_data = [ sr_data[af] for af in log.AF_LIST if af in sr_data ]
  if not af_data:
    af_data = [ f'{kw}: {sr_data[kw]}' for kw in ['node','prefix','pool'] if kw in sr_data ]
  if not af_data and 'nexthop' in sr_data:
    af_data = [ 'nexthop: '+str(sr_data.nexthop)]
  return ','.join(af_data) or 'null'

"""
process_static_routes: Import global static routes into node static routes
"""
def process_static_route_includes(
      o_data: typing.Union[Box,BoxList],
      o_type: str,
      topo_object: Box,
      o_name: str) -> typing.Union[Box,BoxList]:
  if isinstance(o_data,Box):
    for kw in list(o_data.keys()):
      if isinstance(o_data[kw],BoxList):
        o_data[kw] = process_static_route_includes(o_data[kw],o_type,topo_object,o_name)
      else:
        o_data[kw] = process_static_route_includes(BoxList([o_data[kw]]),o_type,topo_object,o_name)
    return o_data
  if not isinstance(o_data,list):
    return o_data

  include_limit = 20
  topology = global_vars.get_topology()
  if topology is None:
    return o_data
  sr_name = 'A global static route list' if topo_object else f'Static route list in node {o_name}'

  while True:
    include_rq = False
    for idx in range(len(o_data)):
      sr_data = o_data[idx]
      if 'include' not in sr_data:
        continue

      if sr_data.include not in topology.get('routing.static',{}):
        log.error(
          f'{sr_name} is trying to include non-existent global static route list {sr_data.include}',
          category=log.MissingValue,
          module='routing')
        sr_data.remove = True
        continue

      include_rq = True
      inc_data = topology.routing.static[sr_data.include]
      for sr_entry in inc_data:        
        if 'nexthop' in sr_data:
          sr_entry = sr_entry + { 'nexthop': sr_data.nexthop }
        o_data.append(sr_entry)

      sr_data.remove = True

    if not include_rq:
      return o_data

    o_data = BoxList([ sr_data for sr_data in o_data if not sr_data.get('remove',False) ])
    include_limit -= 1
    if not include_limit:
      log.error(
        f'{sr_name} has exceeded the include depth limit',
        more_hints='You might have a loop of "include" requests',
        category=log.IncorrectValue,
        module='routing')
      return o_data

"""
Static route import has been done during the normalization phase,
but we still need a fake function for the import/check loop to work
"""
def import_static_routes(idx: int,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  return None

"""
Create next-hop information from neighbor addresses and static route data
"""
def create_nexthop_data(sr_data: Box,ngb_addr: Box, intf: Box) -> Box:
  nh_data = data.get_empty_box()

  for af in log.AF_LIST:
    if af not in ngb_addr:
      continue
    if isinstance(ngb_addr[af],str):
      nh_data[af] = ngb_addr[af]
      nh_data.intf = intf.ifname

  if nh_data and 'vrf' in sr_data.nexthop:
    nh_data.vrf = sr_data.nexthop.vrf

  return nh_data

"""
Extract an address from the NH list into the next-hop information. Further
processing of static routes uses that next-hop information to figure out
whether we have at least one viable next hop for every prefix specified in
the static route
"""
def extract_nh_from_list(nh: Box) -> None:
  for af in log.AF_LIST:
    if af not in nh:
      af_nh = [ nh_entry[af] for nh_entry in nh.nhlist if af in nh_entry ]
      if af_nh:
        nh[af] = af_nh[0]

"""
When a static route uses a node as a next hop, we have to resolve
that into IPv4/IPv6 addresses. This function returns a list of
next hops (IPv4/IPv6/intf) for directly-connected nodes or control-plane
endpoint information for remote next hops.

Please note that the next-hop list is returned as the 'nhlist' attribute
of the 'nexthop' data structure.
"""
def resolve_node_nexthop(sr_data: Box, node: Box, topology: Box) -> Box:
  nh = data.get_empty_box()
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  node_found = False
  for intf in node.interfaces:
    if intf.get('_phantom_link',False):
      continue
    for ngb in intf.neighbors:
      if ngb.node != sr_data.nexthop.node:
        continue

      node_found = True
      if intf.get('vrf',None) != nh_vrf:
        continue

      ngb_addr = extract_af_info(ngb,keep_prefix=False)
      nh_data = create_nexthop_data(sr_data,ngb_addr,intf)

      if nh_data:
        data.append_to_list(nh,'nhlist',nh_data)
  
  if nh:
    extract_nh_from_list(nh)
  else:
    if node_found:
      log.error(
        f'Next hop {sr_data.nexthop.node} for static route "{get_static_route_id(sr_data)}"'+ \
        f' is connected to node {node.name} but not in VRF {nh_vrf or "default"}',
        category=log.IncorrectValue,
        module='routing')

    nh = extract_af_info(
           _routing.get_remote_cp_endpoint(topology.nodes[sr_data.nexthop.node]),
           keep_prefix=False)

  return nh

"""
Create the gateway-of-last-resort: for all missing address families:

* Iterate over interface neighbors
* Skip neighbors that are not routers
* Skip neighbors that have no usable IP address (LLA/unnumbered does not count)
* Skip neighbors that use DHCP clients

If anything is left, use that as the gateway of last resort
"""
def create_gateway_last_resort(intf: Box, missing_af: Box, topology: Box) -> typing.Tuple[Box,bool]:
  gw_data = data.get_empty_box()
  unnum_ngb = False

  # Get roles that can be default gateways
  gw_roles = global_vars.get_const('gateway.roles',['router','gateway'])

  for af in list(missing_af.keys()):                        # Iterate over all missing AFs
    for ngb in intf.neighbors:                              # Iterate over all interface neighbors
      n_node = topology.nodes[ngb.node]
      if n_node.get('role','router') not in gw_roles:       # Host/bridge neighbors are useless
        continue
      if af not in ngb:                                     # Does the neighbor have an address in desired AF?
        continue
      if ngb[af] is True:                                   # Do we have an unnumbered neighbor?
        unnum_ngb = True                                    # Mark that we found a fishy neighbor
        continue
      if not isinstance(ngb[af],str):                       # Is the neighbor IP address a real address?
        continue
      if ngb.get(f'dhcp.client.{af}',False):                # Is neighbor using a DHCP client?
        continue
      gw_data[af] = ngb[af]                                 # Use neighbor as the gateway of last resort
      missing_af.pop(af,None)                               # One less AF to worry about
      break                                                 # And get out of the neighbor loop

  if gw_data:
    intf.gateway = gw_data                                  # Store the cached data
  return (gw_data,unnum_ngb)                                # ... and return it together with fishy ngb flag

"""
When a static route uses a default gateway as a next hop, we have to resolve
that into IPv4/IPv6 addresses. This function returns a list of default gateway
next hops (IPv4/IPv6/intf).

Please note that the next-hop list is returned as the 'nhlist' attribute of the
'nexthop' data structure.

Finally, this function can be called twice, first trying to get the configured
gateway data (using the "gateway" module), and if that fails with a desperate
call to get the gateway of last resort (create_gw set to True).

The "gateway of last resort" functionality tries to find the first usable
adjacent router (one per AF, potentially on different interfaces) and uses
that as the next hop for the 'gateway' static routes. The collected information
is added to the interface data to speed up the lookup for subsequent static
route entries.
"""
def resolve_gateway_nexthop(sr_data: Box, node: Box, topology: Box, create_gw: bool = False) -> Box:
  nh = data.get_empty_box()
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  found_unnum_ngb = False
  if create_gw:                                         # This is a desperate call for gateway-of-last-resort
    missing_af = data.get_box(node.af)                  # ... so we need to keep the track of missing AFs

  for intf in node.interfaces:
    if intf.get('vrf',None) != nh_vrf:                  # Skip interfaces in wrong VRFs
      continue

    gw_data = intf.get('gateway',{})                    # Do we have the gateway information on the interface?
    if not gw_data:                                     # It might not be present on routers using static routes
      gw_list = [ ngb.gateway for ngb in intf.neighbors if 'gateway' in ngb ]
      if gw_list:                                       # ... so we try to get the information from the neighbors
        gw_data = gw_list[0]                            # ... using the 'gateway' module
        intf.gateway = gw_data                          # ... and cache it for further use

    if not gw_data:                                     # No usable gateway information
      if create_gw:                                     # Are we trying to set up gateway of last resort?
        (gw_data,u_ngb) = create_gateway_last_resort(intf,missing_af,topology)
        found_unnum_ngb = found_unnum_ngb or u_ngb
        if not gw_data:                                 # Found no useful gateway of last resort
          continue                                      # ... move to the next interface

    gw_addr = extract_af_info(gw_data,keep_prefix=False)
    nh_data = create_nexthop_data(sr_data,gw_addr,intf)
    if nh_data:
      data.append_to_list(nh,'nhlist',nh_data)

  if nh:
    extract_nh_from_list(nh)
  else:
    if found_unnum_ngb and '_unnum_warning' not in node:
      log.warning(
        text=f'Host {node.name} is attached only to subnets where all routers have unnumbered interfaces',
        category=log.MissingValue,
        module='routing',
        flag='host_gw',
        hint='host_gw')
      node._unnum_warning = True

  return nh

"""
When a static route uses an IPv4 or IPv6 address as the next hop,
we're trying to find the outgoing interface for directly-connected next hops.

We have to do this for platforms like Linux that do not support indirect next hops.

The next-hop list is returned as the 'nhlist' attribute of the 'nexthop' data structure.
"""
def resolve_nexthop_intf(sr_data: Box, node: Box, topology: Box) -> Box:
  nh = sr_data.nexthop
  nh_vrf = sr_data.nexthop.vrf if 'vrf' in sr_data.nexthop else sr_data.get('vrf',None)

  for af in log.AF_LIST:
    if af not in sr_data:
      continue

    nh_addr = ipaddress.ip_interface(nh[af])
    nh_net  = nh_addr.network
    for intf in node.interfaces:                            # Try to find the next-hop interfaces
      if af not in intf or not isinstance(intf[af],str):    # Interface does not have an address in target AF
        continue
      if intf.get('vrf',None) != nh_vrf:                    # Interface is in the wrong VRF
        continue

      # Move on if the next hop does not belong to the interface subnet
      #
      if not nh_net.subnet_of(ipaddress.ip_interface(intf[af]).network):      # type: ignore[arg-type]
        continue

      # Otherwise append the direct next-hop information to the nhlist
      #
      nh_data = data.get_box({ af: nh[af], 'intf': intf.ifname })
      if 'vrf' in sr_data.nexthop:
        nh_data.vrf = sr_data.nexthop.vrf

      data.append_to_list(nh,'nhlist',nh_data)
  
  return nh

"""
Check whether a VRF static route is valid and supported by the device on which it's used
"""
def check_VRF_static_route(sr_data: Box, node: Box, sr_features: Box) -> bool:
  if 'vrf' in sr_data:
    if sr_data.vrf not in node.get('vrfs',{}):
      log.error(
        f'Static route "{get_static_route_id(sr_data)}" in node {node.name}' + \
        f' refers to VRF {sr_data.vrf} which is not defined',
        category=log.IncorrectValue,
        module='routing')
      return False

    if not sr_features.get('vrf',False):
      log.error(
        f'Device {node.device} (node {node.name}) does not support VRF static routes',
        category=log.IncorrectValue,
        module='routing')
      return False
    
  if 'vrf' in sr_data.nexthop:
    if not sr_features.get('inter_vrf',False):
      log.error(
        f'Device {node.device} (node {node.name}) does not support inter-VRF static routes',
        category=log.IncorrectValue,
        module='routing')
      return False
    
    if sr_data.nexthop.vrf and sr_data.nexthop.vrf not in node.get('vrfs',{}):
      log.error(
        f'Next hop of a static route "{get_static_route_id(sr_data)}" in node {node.name}' + \
        f' refers to VRF {sr_data.nexthop.vrf} which is not defined',
        category=log.IncorrectValue,
        module='routing')
      return False
    
  return True

def check_static_routes(idx: int,o_name: str,node: Box,topology: Box) -> None:
  sr_data = node.routing[o_name][idx]
  d_features = devices.get_device_features(node,topology.defaults)
  sr_features = d_features.get('routing.static')
  if not isinstance(sr_features,dict):
    sr_features = data.get_empty_box()

  if 'pool' in sr_data:
    sr_data = sr_data + extract_af_info(topology.addressing[sr_data.pool])
  elif 'prefix' in sr_data:
    sr_data = sr_data + extract_af_info(addressing.evaluate_named_prefix(topology,sr_data.prefix))
  elif 'node' in sr_data:
    sr_data = sr_data + extract_af_info(_routing.get_remote_cp_endpoint(topology.nodes[sr_data.node]))

  if idx == 0:
    check_routing_object(get_static_route_id(sr_data),o_name,node,topology)

  if 'ipv4' not in sr_data and 'ipv6' not in sr_data:
    log.error(
      f'Static route "{get_static_route_id(sr_data)}" in node {node.name} has no usable IPv4 or IPv6 prefix',
      category=log.MissingValue,
      module='routing')
    return

  if 'nexthop' not in sr_data:
    if '_skip_missing' in sr_data:
      sr_data.remove = True
    else:
      log.error(
        f'Static route "{get_static_route_id(sr_data)}" in node {node.name} has no next hop information',
        category=log.MissingValue,
        module='routing')
    return

  if 'vrf' in sr_data or 'vrf' in sr_data.nexthop:
    if not check_VRF_static_route(sr_data,node,sr_features):
      return

  if sr_data.nexthop.get('node',None):
    sr_data.nexthop = resolve_node_nexthop(sr_data,node,topology) + sr_data.nexthop
  elif sr_data.nexthop.get('gateway',None):
    gw_nh = resolve_gateway_nexthop(sr_data,node,topology)
    if not gw_nh:
      gw_nh = resolve_gateway_nexthop(sr_data,node,topology,create_gw=True)
    sr_data.nexthop = gw_nh + sr_data.nexthop
  elif 'ipv4' in sr_data.nexthop or 'ipv6' in sr_data.nexthop:
    resolve_nexthop_intf(sr_data,node,topology)

  for af in ['ipv4','ipv6']:
    if af not in sr_data:
      continue
    
    if af not in sr_data.nexthop:
      if '_skip_missing' in sr_data:
        sr_data.remove = True
      elif 'discard' in sr_data.nexthop:
        if 'discard' in sr_features:
          continue
        log.error(
          f'Device {node.device} (node {node.name}) does not support discard static routes',
          category=log.IncorrectAttr,
          module='routing')        
      else:
        log.error(
          f'A static route for {sr_data[af]} on node {node.name} has no {af} next hop',
          more_data=str(sr_data),
          category=log.MissingValue,
          module='routing')
      return

  if 'nhlist' in sr_data.nexthop:
    sr_data.remove = True
    for af in log.AF_LIST:
      if af not in sr_data:
        continue
      nexthops = [ nh_entry for nh_entry in sr_data.nexthop.nhlist if af in nh_entry ]
      if not nexthops:
        continue
      for (nh_idx,nh_entry) in enumerate(nexthops[:sr_features.get('max_nexthop',256)]):
        sr_entry = data.get_box({ af: sr_data[af], 'nexthop': nh_entry })
        sr_entry.nexthop.idx = nh_idx
        if 'vrf' in sr_data:
          sr_entry['vrf'] = sr_data.vrf

        node.routing[o_name].append(sr_entry)
  else:
    sr_data.nexthop.idx = 0

  node.routing[o_name][idx] = sr_data

def cleanup_static_routes(o_data: BoxList,o_type: str,node: Box,topology: Box) -> None:
  node.routing[o_type] = [ sr_entry for sr_entry in node.routing[o_type] if 'remove' not in sr_entry ]

"""
Dispatch table for post-transform processing. Currently used only to
expand the prefixes/pools in prefix list.
"""
transform_dispatch: typing.Dict[str,dict] = {
  'policy': {
    'import': adjust_routing_policy
  },
  'prefix': {
    'import': expand_prefix_list
  },
  'aspath': {
    'import': number_aspath_acl
  },
  'community': {
    'import': expand_community_list
  },
  'static': {
    'start'  : process_static_route_includes,
    'import' : import_static_routes,
    'check'  : check_static_routes,
    'cleanup': cleanup_static_routes
  }
}

class Routing(_Module):

  """
  Normalize routing object shortcuts into data structures that will pass validation
  This step has to be implemented as a static "normalize" hook to be executed before
  group data validation.
  """
  def module_normalize(self, topology: Box) -> None:
    normalize_routing_data(topology,topo_object=True,o_name='topology')

    for gname,gdata in topology.get('groups',{}).items():
      if gname.startswith('_'):
        continue
      normalize_routing_data(gdata,o_name=f'groups.{gname}')

    for node,ndata in topology.nodes.items():
      normalize_routing_data(ndata,o_name=f'nodes.{node}')

  """
  The routing module defines two standard prefixes in the topology defaults. These
  prefixes have to be merged with topology prefixes before any serious transformation
  work starts.
  """
  def module_pre_default(self, topology: Box) -> None:
    topology.prefix = topology.defaults.prefix + topology.prefix

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global import_dispatch

    for o_name in import_dispatch.keys():
      process_routing_data(node,o_name,topology,import_dispatch,always_check=True)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    global transform_dispatch

    for o_name in transform_dispatch.keys():
      process_routing_data(node,o_name,topology,transform_dispatch)
