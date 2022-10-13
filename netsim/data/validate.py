#
# Data validation routines
#

import typing,typing_extensions
from box import Box
from .. import common
from . import get_from_box,set_dots

# wrong_type_message: return a text message with the name of the incorrect type
#
def wrong_type_text(x : typing.Any) -> str:
  return "dictionary" if isinstance(x,dict) else str(type(x))

def wrong_type_message(
      path: str,                                        # Path to the value
      expected: str,                                    # Expected type
      value: typing.Any,                                # Value we got
      key: typing.Optional[str] = None,                 # Optional key within the object
      context: typing.Optional[typing.Any] = None,      # Optional context
      module:     typing.Optional[str] = None,          # Module name to display in error messages
                      ) -> None:

  wrong_type = wrong_type_text(value)
  path = f'{path}.{key}' if key else path
  ctxt = f'\n... context: {context}' if context else ''
  common.error(
    f'attribute {path} must be {expected}, found {wrong_type}{ctxt}',
    common.IncorrectType,
    module or 'topology')
  return

def int_value_error(
      path: str,                                        # Path to the value
      expected: str,                                    # Expected type
      value: typing.Any,                                # Value we got
      key: typing.Optional[str] = None,                 # Optional key within the object
      context: typing.Optional[typing.Any] = None,      # Optional context
      module:     typing.Optional[str] = None,          # Module name to display in error messages
                      ) -> None:

  path = f'{path}.{key}' if key else path
  ctxt = f'\n... context: {context}' if context else ''
  common.error(
    f'attribute {path} must be {expected}, found {value}{ctxt}',
    common.IncorrectValue,
    module or 'topology')
  return

def check_valid_values(
      path: str,                                        # Path to the value
      expected: list,                                   # Expected values
      value: typing.Any,                                # Value we got
      key: typing.Optional[str] = None,                 # Optional key within the object
      context: typing.Optional[typing.Any] = None,      # Optional context
      module:     typing.Optional[str] = None,          # Module name to display in error messages
                      ) -> bool:

  if isinstance(value,list):                            # Deal with lists first
    f = list(filter(lambda x: x not in expected,value)) # ... find all values not in expected values
    if not f:
      return True                                       # ... no unexpected values, cool, get out of here
    value = ','.join(f)                                 # ... otherwise create something to display
  else:
    if value in expected:                               # Not a list? Just check if the value matches one of expected values
      return True

  path = f'{path}.{key}' if key else path
  ctxt = f'\n... context: {context}' if context else ''
  common.error(
    f'attribute {path} has invalid value(s): {value}\n... valid values are: {",".join(expected)}{ctxt}',
    common.IncorrectValue,
    module or 'topology')
  return False

#
# must_be_list: make sure a dictionary value is a list. Convert scalar values
#   to list if needed, report an error otherwise.
#
# must_be_string: make sure a dictionary value is a string. Throw an error otherwise.
#
# must_be_int: make sure a dictionary value is an integer. Throw an error otherwise.
#
# must_be_dict: make sure a dictionary value is another dictionary. Throw an error otherwise.
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
def must_be_list(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      create_empty: bool = True,                        # Do we want to create an empty list if needed?
      true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_, set _false_ to []
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
      valid_values: typing.Optional[list] = None,       # List of valid values
                ) -> typing.Optional[list]:

  value = get_from_box(parent,key)
  if value is None:
    if create_empty:
      set_dots(parent,key.split('.'),[])
      return parent[key]
    else:
      return None

  if isinstance(value,bool) and not true_value is None:
    value = true_value if value else []
    parent[key] = value

  if isinstance(value,(str,int,float,bool)):
    parent[key] = [ value ]
    value = parent[key]

  if isinstance(value,list):
    if not valid_values is None:
      check_valid_values(path=path, key=key, value=value, expected=valid_values, context=context, module=module)
    return parent[key]

  wrong_type_message(path=path, key=key, expected='a scalar or a list', value=value, context=context, module=module)
  return None

def must_be_dict(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      create_empty: bool = True,                        # Do we want to create an empty list if needed?
      true_value: typing.Optional[dict] = None,         # Value to use to replace _true_, set _false_ to []
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
                ) -> typing.Optional[list]:

  value = get_from_box(parent,key)
  if value is None:
    if create_empty:
      set_dots(parent,key.split('.'),{})
      return parent[key]
    else:
      return None

  if isinstance(value,bool) and not true_value is None:
    value = true_value if value else {}
    parent[key] = value

  if isinstance(value,dict):
    return parent[key]

  wrong_type_message(path=path, key=key, expected='a dictionary', value=value, context=context, module=module)
  return None

def must_be_string(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_, set to "" if _false_
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
      valid_values: typing.Optional[list] = None,       # List of valid values
                ) -> typing.Optional[str]:

  value = get_from_box(parent,key)
  if value is None:
    return None

  if isinstance(value,str):
    if not valid_values is None:
      check_valid_values(path=path, key=key, value=value, expected=valid_values, context=context, module=module)
    return value

  if isinstance(value,bool) and true_value:
    value = true_value if value else ""
    parent[key] = value
    return value

  wrong_type_message(path=path, key=key, expected='a string', value=value, context=context, module=module)
  return None

def must_be_int(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_, remove if _false_
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
      min_value:  typing.Optional[int] = None,          # Minimum value
      max_value:  typing.Optional[int] = None,          # Maximum value
                ) -> typing.Optional[int]:

  value = get_from_box(parent,key)
  if value is None:
    return None

  if isinstance(value,bool) and true_value:
    if value:
      parent[key] = true_value
      return true_value
    else:
      parent.pop(key,None)
      return None

  if not isinstance(value,int):
    wrong_type_message(path=path, key=key, expected='an integer', value=value, context=context, module=module)
    return None

  if isinstance(min_value,int) and isinstance(max_value,int):
    if value < min_value or value > max_value:
      int_value_error(path=path, key=key, expected=f'between {min_value} and {max_value}', value=value, context=context, module=module)
      return None
  elif isinstance(min_value,int):
    if value < min_value:
      int_value_error(path=path, key=key, expected=f'larger or equal to {min_value}', value=value, context=context, module=module)
      return None
  elif isinstance(max_value,int):
    if value > max_value:
      int_value_error(path=path, key=key, expected=f'less than or equal to {max_value}', value=value, context=context, module=module)
      return None

  return value

#
# must_be_bool: check whether a parameter is a boolean value and remove False value
#   to simplify Jinja2 templates
#
# Input arguments:
#   parent - parent dictionary
#   key    - parent dictionary key
#   path   - parent dictionary path (used in error messages)
#
def must_be_bool(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
      valid_values: typing.Optional[list] = None,       # List of valid values
                ) -> None:

  value = get_from_box(parent,key)
  if value is None:
    return None

  if isinstance(value,bool):
    if not value:
      parent.pop(key,None)
    return None

  wrong_type_message(path=path, key=key, expected='a boolean', value=value, context=context, module=module)
  return None


"""
validate_list_elements: check whether the elements of a list belong to a set of predefined values
"""

def validate_list_elements(data: list, values: list, path: str) -> bool:
  if not isinstance(data,list):  # pragma: no cover
    common.fatal(f'{path} should be a list')
    return False
  return all(item in values for item in data)

"""
is_true_int: work around the Python stupidity of bools being ints
"""

def is_true_int(data: typing.Any) -> typing_extensions.TypeGuard[int]:
  return isinstance(data,int) and not isinstance(data,bool)
