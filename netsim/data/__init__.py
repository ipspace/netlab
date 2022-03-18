#
# Generic data model manipulation routines
#

import typing
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

#
# must_be_list: make sure a dictionary value is a list. Convert scalar values
#   to list if needed, report an error otherwise.
#
# Input arguments:
#   parent - the parent dictionary of the attribute we want to listify
#            (a pointer to the element would be even better, but Python)
#   key    - the parent dictionary key
#   path   - path of the parent dictionary that would help the user identify
#            where the problem is
#
# Sample use: make sure the 'config' attribute of a node is list
#
#    must_be_list(node,'config',f'nodes.{node.name}')
#
def must_be_list(parent: Box, key: str, path: str) -> typing.Optional[list]:
  if not key in parent:
    parent[key] = []
    return parent[key]

  if isinstance(parent[key],list):
    return parent[key]

  if isinstance(parent[key],(str,int,float,bool)):
    parent[key] = [ parent[key] ]
    return parent[key]

  wrong_type = "dictionary" if isinstance(parent[key],dict) else str(type(parent[key]))
  common.error(
  	f'attribute {path}.{key} must be a scalar or a list, found {wrong_type}',
  	common.IncorrectType)
  return None

#
# must_be_bool: check whether a parameter is a boolean value and remove False value
#   to simplify Jinja2 templates
#
# Input arguments:
#   parent - parent dictionary
#   key    - parent dictionary key
#   path   - parent dictionary path (used in error messages)
#
def must_be_bool(parent: Box, key: str, path: str) -> None:
  if not key in parent:
    return

  if isinstance(parent[key],bool):
    if not parent[key]:
      parent.pop(key,None)
    return

  common.error(
    f'attribute {path}.{key} must be a boolean, found {str(type(parent[key]))}',
    common.IncorrectType)

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
validate_list_elements: check whether the elements of a list belong to a set of predefined values
"""

def validate_list_elements(data: list, values: list) -> bool:
  return all(item in values for item in data)
