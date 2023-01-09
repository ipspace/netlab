#
# Data validation routines
#

import typing,typing_extensions
import functools
from box import Box
from .. import common
from . import get_from_box,set_dots

"""
Common error checking routines:

* wrong_type_text: return the type of the data item, tranforming Box into dict
* wrong_type_message: prints the 'wrong data type' error message
* int_value_error: prints out-of-bounds error message
* check_valid_values: checks scalar or lists for valid values
"""

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

def check_valid_values(
      path: str,                                        # Path to the value
      expected: list,                                   # Expected values
      value:    typing.Any,                             # Value we got
      key:      typing.Optional[str] = None,            # Optional key within the object
      context:  typing.Optional[typing.Any] = None,     # Optional context
      module:   typing.Optional[str] = None,            # Module name to display in error messages
      abort:    bool = False,
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

  if abort:
    raise common.IncorrectValue()
  return False

"""
type_test decorator function -- simplifies the type testing functions

* Get the value (using parent and key)
* Handle empty and boolean values
* Handle valid values and abort-on-error
"""

def type_test(
      false_value: typing.Optional[typing.Any] = None,
      empty_value: typing.Optional[typing.Any] = None) -> typing.Callable:

  def test_wrapper(test_function: typing.Callable) -> typing.Callable:

    @functools.wraps(test_function)
    def execute_test(
          parent: Box,                                      # Parent object
          key: str,                                         # Key within the parent object, may include dots.
          path: str,                                        # Path to parent object, used in error messages
          context: typing.Optional[typing.Any] = None,      # Additional context (use when verifying link values)
          module: typing.Optional[str] = None,              # Module name to display in error messages
          valid_values: typing.Optional[list] = None,       # List of valid values
          create_empty: typing.Optional[bool] = None,       # Do we need to create an empty value?
          true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_ (false_values used to replace _false_)
          abort: bool = False,                              # Abort on error
          **kwargs: typing.Any) -> typing.Optional[typing.Any]:

      value = get_from_box(parent,key)
      if value is None:
        if create_empty is None and not(empty_value is None):
          create_empty = True
  
        if create_empty is True:
          value = empty_value
          set_dots(parent,key.split('.'),empty_value)
        return value

      if isinstance(value,bool) and not (true_value is None):
        if value:
          value = true_value
        else:
          if false_value is None:
            parent.pop(key,None)
            return None
          else:
            value = false_value

        parent[key] = value

      expected = test_function(value,**kwargs)
      if not expected is True:
        if isinstance(expected,str):
          wrong_type_message(path=path, key=key, expected=expected, value=value, context=context, module=module)
        if abort:
          raise common.IncorrectType()
        return None

      if valid_values:
        check_valid_values(path=path, key=key, value=value, expected=valid_values, context=context, module=module, abort=abort)

      return value

    return execute_test

  return test_wrapper

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
      abort:      bool = False,
                ) -> typing.Optional[list]:

  value = get_from_box(parent,key)
  if value is None:
    if create_empty:
      set_dots(parent,key.split('.'),[])
      return parent[key]
    else:
      if abort:
        raise common.IncorrectValue()
      return None

  if isinstance(value,bool) and not true_value is None:
    value = true_value if value else []
    parent[key] = value

  if isinstance(value,(str,int,float,bool)):
    parent[key] = [ value ]
    value = parent[key]

  if isinstance(value,list):
    if not valid_values is None:
      check_valid_values(path=path, key=key, value=value, expected=valid_values, context=context, module=module, abort=abort)
    return parent[key]

  wrong_type_message(path=path, key=key, expected='a scalar or a list', value=value, context=context, module=module)
  if abort:
    raise common.IncorrectType()

  return None

def must_be_dict(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      path: str,                                        # Path to parent object, used in error messages
      create_empty: bool = True,                        # Do we want to create an empty list if needed?
      true_value: typing.Optional[dict] = None,         # Value to use to replace _true_, set _false_ to []
      context:    typing.Optional[typing.Any] = None,   # Additional context (use when verifying link values)
      module:     typing.Optional[str] = None,          # Module name to display in error messages
      abort:      bool = False                          # Crash on error
                ) -> typing.Optional[list]:

  value = get_from_box(parent,key)
  if value is None:
    if create_empty:
      set_dots(parent,key.split('.'),{})
      return parent[key]
    else:
      if abort:
        raise common.IncorrectValue()
      return None

  if isinstance(value,bool) and not true_value is None:
    value = true_value if value else {}
    parent[key] = value

  if isinstance(value,dict):
    return parent[key]

  wrong_type_message(path=path, key=key, expected='a dictionary', value=value, context=context, module=module)

  if abort:
    raise common.IncorrectType()

  return None

@type_test(false_value='')
def must_be_string(value: typing.Any) -> typing.Union[bool,str]:
  return True if isinstance(value,str) else 'a string'

@type_test()
def must_be_int(
      value: typing.Any,
      min_value:  typing.Optional[int] = None,          # Minimum value
      max_value:  typing.Optional[int] = None,          # Maximum value
                ) -> typing.Union[bool,str]:

  if not isinstance(value,int):                         # value must be an int
    return 'an integer'

  if isinstance(value,bool):                            # but not a bool
    return 'a true integer (not a bool)'

  if isinstance(min_value,int) and isinstance(max_value,int):
    if value < min_value or value > max_value:
      return 'an integer between {min_value} and {max_value}'
  elif isinstance(min_value,int):
    if value < min_value:
      return 'an integer larger or equal to {min_value}'
  elif isinstance(max_value,int):
    if value > max_value:
      return 'an integer less than or equal to {max_value}'

  return True

@type_test()
def must_be_bool(value: typing.Any) -> typing.Union[bool,str]:
  return True if isinstance(value,bool) else 'a boolean'

"""
is_true_int: work around the Python stupidity of bools being ints
"""

def is_true_int(data: typing.Any) -> typing_extensions.TypeGuard[int]:
  return isinstance(data,int) and not isinstance(data,bool)

