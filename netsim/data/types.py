#
# Data validation routines
#

import typing,typing_extensions,types
import functools
import netaddr
import re
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
  return "dictionary" if isinstance(x,dict) else str(type(x).__name__)

def get_element_path(parent: str, element: typing.Optional[str]) -> str:
  if element:
    return f'{parent}.{element}' if parent else element
  else:
    return parent

def wrong_type_message(
      path: str,                                        # Path to the value
      expected: str,                                    # Expected type
      value: typing.Any,                                # Value we got
      key: typing.Optional[str] = None,                 # Optional key within the object
      context: typing.Optional[typing.Any] = None,      # Optional context
      module:     typing.Optional[str] = None,          # Module name to display in error messages
                      ) -> None:

  wrong_type = wrong_type_text(value)
  path = get_element_path(path,key)
  ctxt = f'\n... context: {context}' if context else ''
  wrong_value = 'NWT: ' in expected
  if wrong_value:                                       # String with 'NWT' means 'type is OK, value is incorrect'
    expected = expected.replace('NWT: ','')             # ... but we also don't want NWT in the error message ;)
  else:
    expected += f', found {wrong_type}'                 # A more generic message, add wrong type

  common.error(
    f'attribute {path} must be {expected}{ctxt}',
    common.IncorrectValue if wrong_value else common.IncorrectType,
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

  path = get_element_path(path,key)
  ctxt = f'\n... context: {context}' if context else ''
  common.error(
    f'attribute {path} has invalid value(s): {value}\n... valid values are: {",".join(expected)}{ctxt}',
    common.IncorrectValue,
    module or 'topology')

  if abort:
    raise common.IncorrectValue()
  return False

"""
is_true_int: work around the Python stupidity of bools being ints
"""

def is_true_int(data: typing.Any) -> typing_extensions.TypeGuard[int]:
  return isinstance(data,int) and not isinstance(data,bool)

"""
type_test decorator function -- simplifies the type testing functions

* Get the value (using parent and key)
* Handle empty and boolean values
* Handle valid values and abort-on-error

Required input arguments:

  parent - the parent dictionary of the attribute we want to listify
           (a pointer to the element would be even better, but Python)
  key    - the parent dictionary key
  path   - path of the parent dictionary that would help the user identify
           where the problem is

Optional arguments:

  context       - Additional data identifying the context (usually used for links)
  module        - The caller module (used for error messages)
  valid_values  - list of valid values (applicable to all data types)
  create_empty  - Create an empty element if the value is missing
  true_value    - Replace True with another value
  abort         - Throw an exception after printing an error message

Sample use: make sure the 'config' attribute of a node is list

  must_be_list(node,'config',f'nodes.{node.name}')

"""

def type_test(
      false_value: typing.Optional[typing.Any] = None,
      empty_value: typing.Optional[typing.Any] = None) -> typing.Callable:

  def test_wrapper(test_function: typing.Callable) -> typing.Callable:

    # Generic data type validation framework
    #
    # Use it as a decorator wrapper around the actual testing function
    #
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

      value = get_from_box(parent,key)                      # Try to get the value from the parent object
      if value is None:                                     # No value was found, now what?
        if empty_value is not None:                         # ... is there empty value for this data type?
          if create_empty is None:                          # Empty value is defined, and we'll use it to create an empty object if the caller
            create_empty = True                             # did not specify its preferencehs
    
          if create_empty:                                  # Now for the real deal
            value = empty_value                             # ... if we should create an empty value do so
            set_dots(parent,key.split('.'),empty_value)     # ... and store it in the parent object (dedottifying the key)
          else:
            if abort:                                       # Empty value was specified, 'create_empty' is False, and there's no actual value
              raise common.IncorrectValue()                 # ... raise an exception if requested

        if not key in parent:                               # We can skip the validation of the key is missing.
          return value                                      # ... if the key is there, then we have to make sure the value is valid

      # Handle boolean-to-data-type conversions if the value is bool and the caller specified true_value
      #
      if isinstance(value,bool) and not (true_value is None):
        if value is True:                                   # Replace True with true_value and move on
          value = true_value
        else:
          if false_value is None:                           # If there's no false_value pop the bool option and return None
            parent.pop(key,None)
            return None
          else:
            value = false_value                             # ... otherwise set the false value

        parent[key] = value

      expected = test_function(value,**kwargs)              # Now call the validator function with the item value

      # Validator function could return:
      #
      # * True -- everything is OK
      # * False -- failed the validation, error message was already printed
      # * string -- error message
      # * callable -- a function returning a replacement value
      #
      if isinstance(expected,(bool,str)):
        if not expected is True:
          if isinstance(expected,str):
            wrong_type_message(path=path, key=key, expected=expected, value=value, context=context, module=module)
          if abort:
            raise common.IncorrectType()
          return None
      elif isinstance(expected,types.FunctionType):
        value = expected(value)
        parent[key] = value
      else:
        common.fatal(f'Validator function {test_function} returned unexpected value {expected}')

      # Finally, check valid values (if specified)
      #
      if valid_values:
        check_valid_values(path=path, key=key, value=value, expected=valid_values, context=context, module=module, abort=abort)

      # And return whatever the final value is (considering empty, true, and transformed values)
      #
      return value

    return execute_test

  return test_wrapper

"""
Individual data type validators
===============================

Most validators check the instance type and return a string error message

Exceptions:

* List validator returns a transformation function when a scalar could be converted to a list
* Integer validation can include minimum/maximum values
"""

@type_test(false_value=[],empty_value=[])
def must_be_list(value: typing.Any) -> typing.Union[bool,str,typing.Callable]:

  def transform_to_list(value: typing.Any) -> list:
    return [ value ]

  if isinstance(value,(str,int,float,bool)):            # Handle scalar-to-list transformations with a callback function
    return transform_to_list

  return True if isinstance(value,list) else 'a scalar or a list'

@type_test(false_value={},empty_value={})
def must_be_dict(value: typing.Any) -> typing.Union[bool,str,typing.Callable]:
  return True if isinstance(value,dict) else 'a dictionary'

@type_test(false_value='')
def must_be_string(value: typing.Any) -> typing.Union[bool,str]:
  return True if isinstance(value,str) else 'a string'

@type_test(false_value='')
def must_be_str(value: typing.Any) -> typing.Union[bool,str]:
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
    return 'NWT: a true integer (not a bool)'

  if isinstance(min_value,int) and isinstance(max_value,int):
    if value < min_value or value > max_value:
      return f'NWT: an integer between {min_value} and {max_value}'
  elif isinstance(min_value,int):
    if value < min_value:
      return f'NWT: an integer larger or equal to {min_value}'
  elif isinstance(max_value,int):
    if value > max_value:
      return f'NWT: an integer less than or equal to {max_value}'

  return True

@type_test()
def must_be_bool(value: typing.Any) -> typing.Union[bool,str]:
  return True if isinstance(value,bool) else 'a boolean'

@type_test()
def must_be_asn(value: typing.Any) -> typing.Union[bool,str]:
  err = 'an AS number (integer between 1 and 65535)'
  if not isinstance(value,int) or isinstance(value,bool):             # value must be an int
    return err

  if value < 0 or value > 65535:
    return 'NWT: '+err

  return True

#
# Testing for IPv4 and IPv6 addresses is nasty, as netaddr module happily mixes IPv4 and IPv6
#
@type_test()
def must_be_ipv4(value: typing.Any, use: str) -> typing.Union[bool,str]:
  if isinstance(value,bool):                                          # bool values are valid only on interfaces
    if use not in ('interface','prefix'):
      return 'NWT: an IPv4 address (boolean value is valid only on an interface)'
    else:
      return True

  if isinstance(value,int):                                           # integer values are valid only as IDs (OSPF area)
    if use not in ('id','interface'):
      return 'NWT: an IPv4 prefix (integer value is only valid as a 32-bit ID)'
    if value < 0 or value > 2**32-1:
      return 'NWT: an IPv4 address or an integer between 0 and 2**32'
    return True

  if not isinstance(value,str):
    return 'IPv4 prefix' if use == 'prefix' else 'IPv4 address'

  if '/' in value:
    if use == 'id':                                                   # IDs should not have a prefix
      return 'NWT: IPv4 address (not prefix)'
  else:
    if use == 'prefix':                                               # prefix must have a /
      return 'NWT: IPv4 prefix'

  try:
    parse = netaddr.IPNetwork(value)                                  # now let's check if we have a valid address
  except Exception as ex:
    return "NWT: IPv4 " + ("address or " if use != 'prefix' else "") + "prefix"

  try:                                                                # ... and finally we have to check it's a true IPv4 address
    parse.ipv4()
    if parse.is_ipv4_mapped():
      return "NWT: IP address in IPv4 format"
  except Exception as ex:
    return "NWT: IPv4 address/prefix"

  return True

@type_test()
def must_be_ipv6(value: typing.Any, use: str) -> typing.Union[bool,str]:
  if isinstance(value,bool):                                          # bool values are valid only on interfaces
    if use not in ('interface','prefix'):
      return 'NWT: an IPv6 address (boolean value is valid only on an interface)'
    else:
      return True

  if isinstance(value,int):                                           # integer values are valid only as IDs (OSPF area)
    if use not in ('interface'):
      return 'NWT: an IPv6 prefix (integer value is only valid as an inteface offset)'
    return True

  if not isinstance(value,str):
    return 'IPv6 prefix' if use == 'prefix' else 'IPv6 address'

  if not '/' in value:
    if use == 'prefix':                                               # prefix must have a /
      return 'NWT: IPv6 prefix (not an address)'

  try:
    parse = netaddr.IPNetwork(value)                                  # now let's check if we have a valid address
  except Exception as ex:
    return "NWT: IPv6 " + ("address or " if use != 'prefix' else "") + "prefix"

  if parse.is_ipv4_mapped():                                          # This is really an IPv4 address, but it looks like IPv6, so OK
    return True

  try:                                                                # ... and finally we have to check it's a true IPv6 address
    parse.ipv4()
    return "NWT: IPv6 (not an IPv4) address"                          # If we could get IPv4 address out of it, it clearly is not
  except Exception as ex:
    pass

  return True

@type_test()
def must_be_mac(value: typing.Any) -> typing.Union[bool,str]:
  if not isinstance(value,str):
    return 'MAC address'

  try:
    parse = netaddr.EUI(value)                                        # now let's check if we have a MAC address
  except Exception as ex:
    return "MAC address"

  return True

@type_test()
def must_be_net(value: typing.Any) -> typing.Union[bool,str]:
  if not isinstance(value,str):
    return 'IS-IS NET/NSAP'

  if not re.fullmatch('[0-9a-f.]+',value):
    return 'NWT: IS-IS NET/NSAP containing hexadecimal digits or dots'

  if len(value.replace('.','')) % 2 != 0:
    return 'NWT: IS-IS NET/NSAP containing even number of hexadecimal digits'

  return True

@type_test()
def must_be_rd(value: typing.Any) -> typing.Union[bool,str]:
  if isinstance(value,int) or value is None:                          # Accept RD/RT offets and trust the modules to do the right thing
    return True                                                       # Also: RD set to None can be used to prevent global-to-node RD inheritance

  if not isinstance(value,str):                                       # Otherwise it must be a string
    return "route distinguisher"

  try:
    (rdt,rdi) = value.split(':')
  except Exception as ex:
    return "NWT: route distinguisher in asn:id or ip:id format"

  try:
    rdi_parsed = int(rdi)
  except Exception as ex:
    return "NWT: an RD in asn:id or ip:id format where id is an integer value"

  try:
    rdt_parsed = int(rdt)
  except Exception as ex:
    try:
      if '/' in rdt:
        return "route distinguisher in asn:id or ip:id format"
      netaddr.IPNetwork(rdt)
    except Exception as ex:
      return "NWT: an RD in asn:id or ip:id format where asn is an integer or ip is an IPv4 address"

  return True
