#
# Generic data model manipulation outines
#

import typing,typing_extensions
from box import Box
from .. import common

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
# Safe get from a hierarchical dictionary (won't create new objects)
#

def get_from_box(b: Box, selector: typing.Union[str,typing.List[str]], partial: bool = False) -> typing.Optional[typing.Any]:
  if isinstance(selector,str):
    selector = selector.split('.')

  for idx,k in enumerate(selector):
    if not k in b:
      return b if partial and idx > 0 else None   # return partial result if request assuming we got at least one match before

    if not isinstance(b[k],dict):                                       # we are at a leaf node
      return b[k] if partial or idx == len(selector) - 1 else None      # ... return the value if we're at the end of
                                                                        # ... the chain or accept partial lookup
    b = b[k]

  return b

#
# Get a global setting or corresponding system default. Use for attributes that are not propagated or early in the
# transformation logic when the module attributes haven't been propagated yet
#

def get_global_parameter(topology: Box, selector: str) -> typing.Optional[typing.Any]:
  value = get_from_box(topology,selector)
  if value is None:
    return get_from_box(topology.defaults,selector)
  else:
    return value

#
# Set a dictionary value specified by a list of keys
#
def set_dots(b : dict,k_list : list,v : typing.Any) -> None:
  if len(k_list) <= 1:
    b[k_list[0]] = v
    return
  if not k_list[0] in b:
    b[k_list[0]] = {}
  elif b[k_list[0]] is None:
    b[k_list[0]] = {}
  set_dots(b[k_list[0]],k_list[1:],v)

#
# Change dotted dictionary keys into nested dictionaries
#
def unroll_dots(b : typing.Any) -> None:
  if isinstance(b,dict):
    for k in list(b.keys()):
      unroll_dots(b[k])
      if isinstance(k,str) and ('.' in k):
        v = b[k]
        del b[k]     # If you're using Box with box_dots parameter
        set_dots(b,k.split('.'),v)
  elif isinstance(b,list):
    for v in b:
      unroll_dots(v)
  else:
    return

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
