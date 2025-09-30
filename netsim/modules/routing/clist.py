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
from .normalize import (
  import_routing_object,
)

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
