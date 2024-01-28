#
# Generic data model manipulation outines
#

import typing,typing_extensions
from box import Box
from . import types

#
# I had enough -- here's a function that returns a box with proper default settings

def get_box(init: dict) -> Box:
  return Box(init,default_box=True,default_box_none_transform=False,box_dots=True)

def get_empty_box() -> Box:
  return get_box({})

#
# Another thingy we need all the time: make something a list

def get_a_list(x: typing.Any, ctx: typing.Optional[str] = None) -> list:
  if isinstance(x,list):
    return x
  if isinstance(x,dict):
    from ..utils import log
    log.fatal(f'Internal error: expected something that could be made into a list, got {x}')

  return [ x ]

#
# Change all NULL values in a nested dictionary structure to empty strings
# to make them nicer in YAML printouts
#
def null_to_string(d: typing.Dict) -> None:
  for k in d.keys():
    if isinstance(d[k],dict):
      null_to_string(d[k])
    elif d[k] is None:
      d[k] = ""

#
# Recursively remove null values from a box
#

def remove_null_values(d: Box) -> None:
  for k in list(d.keys()):                                  # Iterate over box keys
    if d[k] is None:
      d.pop(k)                                              # Remove null values
    elif isinstance(d[k],Box):
      remove_null_values(d[k])                              # ... and recurse into child boxes

#
# Get a global setting or corresponding system default. Use for attributes that are not propagated or early in the
# transformation logic when the module attributes haven't been propagated yet
#
# Use 'get_global_parameter' to get a single value and 'get_global_settings' to get a merged dictionary of
# default and topology settings
#
# Use 'get_global_settings' when you need a dictionary of global module parameters if the module uses
# 'no_propagate' flag to stop leaking into nodes.
#

def get_global_parameter(topology: Box, selector: str) -> typing.Optional[typing.Any]:
  try:
    return topology.get(selector,None) or topology.defaults.get(selector,None)
  except:
    return None

def get_global_settings(topology: Box, selector: str) -> typing.Optional[typing.Any]:
  try:                                                                # Wrapping 'get' operations in tries
    g_set = topology.get(selector,None)                               # ... because they may fail if an intermediate
  except:                                                             # ... value is not a dictionary
    g_set = None

  try:
    d_set = topology.defaults.get(selector,None)
  except:
    d_set = None

  if d_set:                                                           # Found default settings
    if 'attributes' in d_set:                                         # ... filter them down to actual global attributes
      d_set = get_box({ k:v for k,v in d_set.items() if k in d_set.attributes['global'] })
  else:                                                               # No default settings? Just return the g_set
    return g_set

  if g_set is None:                                                   # No global settings, go for default whatever it is
    return d_set

  if isinstance(g_set,Box) and isinstance(d_set,Box):                 # We can merge two boxes but nothing else
    return d_set + g_set                                              # Return a merged value, be careful about precedences

  return g_set                                                        # Can't merge, and we know g_set has some value

"""
bool_to_defaults: 

* remove a parameter set to False just to prevent default propagation
* replace a True value with a default dictionary
* dive recursively into all keys specified in default dictionary
"""

def bool_to_defaults(obj: Box, attr: str, defvalue: typing.Optional[typing.Any] = None) -> None:
  if not attr in obj:                   # Attribute not in dictionary, nothing to do
    return

  if isinstance(obj[attr],Box):
    for k in list(obj[attr].keys()):
      if isinstance(defvalue,dict) and k in defvalue:
        bool_to_defaults(obj[attr],k,defvalue[k])
    return

  if not isinstance(obj[attr],bool):    # Attribute not a boolean, no further work needed
    return

  if not obj[attr]:                     # Remove False value
    obj.pop(attr,None)
    return

  if not defvalue is None:              # If the default value was specified, replace True with default value
    obj[attr] = defvalue

"""
is_true_int: work around the Python stupidity of bools being ints
"""

def is_true_int(data: typing.Any) -> typing_extensions.TypeGuard[int]:
  return isinstance(data,int) and not isinstance(data,bool)

"""
find_in_list: Find if any of the specified elements is in list, return index or None
"""

def find_in_list(value: list, target: list) -> typing.Optional[int]:
  for v in value:
    try:
      return target.index(v)
    except:
      continue

  return None

"""
Lookup a netlab keyword, return a list of device keyword(s)
"""
def kw_lookup(lookup_table: typing.Union[dict,Box], kw: str) -> list:
  if not kw in lookup_table:                      # Do we know what to do?
    return []                                     # ... nope, it's better to skip this one
  
  v = lookup_table[kw]                            # Get the lookup value
  if v is None or v is True:                      # No translation, use the original keyword
    return [ kw ]
  elif v is False:                                # This keyword is not supported, skip it
    return []
  else:
    return v if isinstance(v,list) else [ v ]     # ... otherwise return the translated value as a list

def kw_list_transform(lookup_table: typing.Union[dict,Box], kw_list: list) -> list:
  xf_list = []
  for kw in kw_list:
    for lookup_kw in kw_lookup(lookup_table,kw):
      if not lookup_kw in xf_list:
        xf_list.append(lookup_kw)

  return xf_list
