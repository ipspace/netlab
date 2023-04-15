#
# This module handles file map - lists of strings in a:b format - that
# are used in clab to map files from the host to the container.
#
# We used to store them in boxes, but that stopped being an option with
# python-box 7.0 (or so) that started turning dotted keys into hierarchies.
#

import typing
from box import Box
from ..utils.log import error,IncorrectType,IncorrectValue
from ..data.types import must_be_list,must_be_dict

"""
Convert a box into a traditional dictionary, turning a hierarchy
into keys with dots in them.
"""
def box_to_dict(b: Box) -> dict:
  cvalue: dict = {}
  for k in list(b.keys()):
    v = b[k]
    while isinstance(v,dict) and len(v) == 1:
      k = k + '.' + list(v.keys())[0]
      v = list(v.values())[0]
    cvalue[k] = v

  return cvalue

"""
Convert a dictionary into a file mapping -- list of strings in a:b format
"""
def dict_to_mapping(d: typing.Union[Box,dict]) -> list:
  return [ f"{k}:{v}" for k,v in d.items() ]

"""
Convert a file mapping -- list of strings in a:b format -- into a dictionary
"""
def mapping_to_dict(m: list) -> dict:
  return { k:v for k,v in [ l.split(':') for l in m ] }

"""
Check mapping list -- it must be a list of strings, and each string must have exactly one :
"""
def check_mapping_list(map_list: list, path: str, module: str) -> bool:
  OK = True
  for (idx,value) in enumerate(map_list):
    if not isinstance(value,str):
      error(
        f"{path}[{idx+1}] should be a string, found {type(value)}",
        category=IncorrectType,
        module=module)
      OK = False
      continue
    vals = value.split(':')
    if len(vals) != 2:
      error(
        f"{path}[{idx+1}] should be a string in host:target format, found {value}",
        category=IncorrectValue,
        module=module)
      OK = False
      continue

  return OK

"""
Check mapping dict -- it must be a dictionary, and each key must be a string
"""
def check_mapping_dict(value: dict, path: str, module: str) -> bool:
  OK = True
  for k,v in value.items():
    if not isinstance(v,str):
      error(
          f"{path}.{k} should be a string, found {type(v)}",
          category=IncorrectType,
          module=module)
      OK = False

  return OK

"""
Normalize file mapping:

* Validate its value: it must be a list of strings in a:b format, or a dictionary of strings
* Convert it into a list of strings in a:b format
"""
def normalize_file_mapping(parent: Box, path: str, key: str, module: str) -> None:
  if not key in parent:
    return
  
  value = parent[key]
  if value is None:
    parent[key] = []
    return

  if isinstance(value,Box):
    value = box_to_dict(value)
    if not check_mapping_dict(value,f'{path}.{key}',module):
      parent[key] = []
      return
    parent[key] = dict_to_mapping(value)
  elif isinstance(value,list):
    if not check_mapping_list(value,f'{path}.{key}',module):
      parent[key] = []
  else:
    error(
      f"{path}.{key} should be a list of strings in a:b format or a dictionary of strings, found {type(value)}",
      category=IncorrectType,
      module=module)