#
# This module handles file map - lists of strings in a:b format - that
# are used in clab to map files from the host to the container.
#
# We used to store them in boxes, but that stopped being an option with
# python-box 7.0 (or so) that started turning dotted keys into hierarchies.
#

import typing

from box import Box

from ..utils.log import IncorrectType, IncorrectValue, error, fatal

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
Normalize an item in file mapping
"""
def normalize_item(
      path: str,
      module: typing.Optional[str] = None,
      key: typing.Optional[str] = None,
      value: typing.Optional[str] = None,
      line: typing.Optional[str] = None) -> typing.Optional[dict]:
  if line:
    if not ':' in line:
      error(
        f'Invalid line item in {path}: {line}',
        category=IncorrectValue,
        more_hints='The list values should be in source:target format',
        module=module)
      return None
    k,v = line.split(':',maxsplit=1)
  elif key and value:
    k = key
    v = value
  else:
    fatal('INTERNAL ERROR: normalize_item called without line or key/value')

  k = k.replace('@','.')
  item = { 'source': k }
  if ':' in v:
    item['target'],item['mode'] = v.split(':',maxsplit=1)
  else:
    item['target'] = v

  return item

"""
Normalize file mapping:

* Validate its value: it must be a list of strings in a:b format, or a dictionary of strings
* Convert it into a list of strings in a:b format
"""
def normalize_file_mapping(parent: Box, path: str, key: str, module: str) -> None:
  if not key in parent:
    return
  
  path = f'{path}.{key}'
  value = parent[key]
  if value is None:
    parent[key] = []
    return

  if isinstance(value,Box):
    value = box_to_dict(value)
    parent[key] = []
    if not check_mapping_dict(value,path,module):
      return
    for k,v in value.items():
      item = normalize_item(key=k, value=v, path=path, module=module)
      if item:
        parent[key].append(item)
  elif isinstance(value,list):
    xform_list = []
    for line in value:
      if not isinstance(line,str):
        error('An entry in a {path} list should be a string',IncorrectType,module)
        continue
      item = normalize_item(line=line,path=path,module=module)
      if item:
        xform_list.append(item)
    parent[key] = xform_list
  else:
    error(
      f"{path}.{key} should be a list of strings in a:b format or a dictionary of strings, found {type(value)}",
      category=IncorrectType,
      module=module)