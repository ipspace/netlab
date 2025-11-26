#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import re
import typing

from box import Box

from ...augment import devices
from ...utils import log

"""
replace_community_delete:

* replace 'delete.community' with 'delete.community.list' if the 'delete.community' feature is set to 'clist'
* create a new community list if needed
"""
def replace_community_delete(node: Box, p_name: str, p_entry: Box, topology: Box) -> None:
  if not p_entry.get('delete.community',None):
    return
  features = devices.get_device_features(node,topology.defaults)
  if features.get('routing.policy.delete.community') != 'clist':
    return

  clist = []
  for type in ['standard','large','extended']:
    if type not in p_entry.delete.community:
      continue
    elif not features.get(f'routing.community.{type}'):
      log.error(
        f'Node {node.name} (device {node.device}) cannot delete {type} BGP communities in a routing policy',
        more_data=f'Policy {p_name} sequence# {p_entry.sequence}',
        category=log.IncorrectType,
        module='routing')
    else:
      clist += [ { 'action': 'permit', '_value': i } for i in p_entry.delete.community[type] ]

    if clist:
      cname = f"DEL_{type}_{p_name}_{p_entry.sequence}"
      node.routing.community[cname] = { 'type': type, 'cl_type': 'standard', 'value': clist }
      p_entry.delete.community.list[type] = cname
  
  for kw in ['standard','large','extended']:
    p_entry.delete.community.pop(kw, None)

"""
fix_clist_entry: Fix an entry in the BGP community list.

When done, the entry will have:

* _value  -- set to whatever value user specified in regexp, list, or (internal) path attribute
* _regexp -- set if the value is a regular expression
"""
class MissingQuotes(Exception):
  pass

def fix_clist_entry(e_clist: Box, topology: Box) -> None:
  if '_value' in e_clist:                                   # Is this entry already in the expected format?
    return
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

  p_clist.cl_type = 'expanded' if regexp else 'standard'    # Set clist type for devices that use standard/expanded
  p_clist.regexp = 'regexp' if regexp else ''               # And regexp flag for devices that use something else

  return None                                               # Message to caller: no need to do additional checks

"""
check_match_clist_type: check that the community list type used in policy match.community matches the
community list type
"""
def check_match_clist_type(node: Box, p_name: str, p_entry: Box, topology: Box) -> None:
  m_clist = p_entry.get('match.community',None)
  if not isinstance(m_clist,Box):
    return 
  for cl_type,cl_name in m_clist.items():
    clist = node.get(f'routing.community.{cl_name}',None)
    if clist is None:
      continue
    if clist.type != cl_type:
      log.error(
        f'Cannot use {clist.type} community list {cl_name} in match.community.{cl_type}',
        more_data=f'node {node.name} routing policy {p_name} sequence #{p_entry.sequence}',
        module='routing',
        category=log.IncorrectType)

"""
check_community_support: check that the community lists defined on a node can be
configured on that node
"""
def check_community_support(o_data: Box,o_type: str,node: Box,topology: Box) -> None:
  features = devices.get_device_features(node,topology.defaults)
  c_features = features.get('routing.community',None)
  if not c_features or c_features is True:        # When set to True, all community list features are supported
    return                                        # ... when falsy, an error was already generated

  for cl_name,cl_def in o_data.items():           # Not sure yet, so let's iterate over all community lists
    c_type = cl_def.type                          # ... get community type (standard/extended/large)
    l_type = cl_def.cl_type                       # ... and filter type (standard/expanded)
    if c_type not in c_features or not c_features[c_type]:
      log.error(
        f'Device {node.device}/node {node.name} does not support {c_type} BGP community lists: {cl_name}',
        module='routing',
        category=log.IncorrectType)
      continue
    if c_features[c_type] is True:                # Unconditional support (standard/extended)
      continue
    if l_type not in c_features[c_type]:
      log.error(
        f'Device {node.device}/node {node.name} does not support {l_type} {c_type} BGP community lists: {cl_name}',
        module='routing',
        category=log.IncorrectType)
