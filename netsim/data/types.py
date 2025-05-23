#
# Data validation routines
#

import typing,typing_extensions
import functools
import ipaddress
import netaddr
import re
import textwrap

from box import Box
from ..utils import log
from . import global_vars,append_to_list

"""
Common error checking routines:

* get_element_path: given prefix and suffix (either one could be missing) return the full path
* resolve_const_value: when given a string, try to use it as a constant, otherwise return initial value
* init_wrong_type: initialize the error message caches
* wrong_type_text: return the type of the data item, tranforming Box into dict
* wrong_type_message: prints the 'wrong data type' error message
* int_value_error: prints out-of-bounds error message
* check_valid_values: checks scalar or lists for valid values
"""

def get_element_path(parent: str, element: typing.Optional[str]) -> str:
  if not element:                                 # Element missing, return just the parent (whatever it is)
    return parent
  else:
    if not parent:                                # We have suffix but no prefix, get out of here
      return element

    # The fun part: merge prefix + suffix and get rid of unneeded 'topology.' prefix
    path = f'{parent}.{element}'
    return path.replace('topology.','') if path.startswith('topology.') else path

def resolve_const_value(value: typing.Any, default: typing.Optional[typing.Any]) -> typing.Any:
  if not isinstance(value,str):
    return value
  return global_vars.get_const(value,default if default is not None else value)  

_wrong_type_help: dict = {}                           # Remember the 'wrong type' hints we printed out
_attr_help_cache: typing.Optional[Box] = None         # Remember which attribute help messages we already printed out

def init_wrong_type() -> None:
  global _wrong_type_help,_attr_help_cache

  _wrong_type_help = {}
  _attr_help_cache = None

def wrong_type_text(x : typing.Any) -> str:
  return "dictionary" if isinstance(x,dict) else str(type(x).__name__)

def err_add_alt_types(ctx: dict) -> str:
  a_types = ctx.get('_alt_types',[])
  if not a_types:
    return ''

  if len(a_types) == 1:
    return f' or {a_types[0]}'
  else:
    return f' or any of {", ".join(a_types)}'

def wrong_type_message(
      path: str,                                        # Path to the value
      err_stat: dict,                                   # Expected type/value
      value: typing.Any,                                # Value we got
      key: typing.Optional[str] = None,                 # Optional key within the object
      context: dict = {},                               # Optional validation context
      data_name: typing.Optional[str] = None,           # Name of the attribute we're validating
      module: typing.Optional[str] = None,              # Module name to display in error messages
                      ) -> None:
  global _wrong_type_help
  global _attr_help_cache

  wrong_type = wrong_type_text(value)
  path = get_element_path(path,key)
  ctxt = []
  exp_type = err_stat.get('_type','UnSpec')             # _type should be set to expected type on type validation error
  expected = exp_type

  if '_type' not in err_stat and '_value' not in err_stat:
    raise Exception("FATAL (wrong_type_message) err_stat does not contain _type or _value")

  if '_help' in context:
    ctxt.extend(textwrap.wrap(context['_help']))
  elif '_help' in err_stat:                             # Did the validation function specify extra help?
    if exp_type not in _wrong_type_help:                # Did we print this help before? Adjust context if not
      help = err_stat.get("_help")
      ctxt.extend(textwrap.wrap(f'FYI: {exp_type} is {help}'))
      _wrong_type_help[exp_type] = help

  if '_hint' in context:
    ctxt.extend(textwrap.wrap(context['_hint']))

  if '_value' in err_stat:                             # _value contains explanation why the value is incorrect
    expected = err_stat.get('_value')                  # ... even though the type is correct
  else:
    if isinstance(context,dict) and '_alt_types' in context:
      expected += err_add_alt_types(context)
      ctxt = []
    expected += f', found {wrong_type}'                 # A more generic message, add wrong type

  if 'NOATTR:' in path:                                 # Deal with values that are not attributes
    path = path.replace('NOATTR:','')
  else:
    path = f"attribute '{path}'"

  # Display hint only when we know the hint ID
  if '_hint_id' in err_stat:
    if _attr_help_cache is None:                        # Initialize help messages cache if needed
      from ..data import get_empty_box
      _attr_help_cache = get_empty_box()

    hint_id = err_stat.get('_hint_id') or 'SomeHint'    # ... just in case we have some weird value in the hint ID
    if not _attr_help_cache.hints[hint_id]:             # Did we already display this hint?
      ctxt.append(err_stat.get('_hint',''))             # ... nope, time to do it now
      _attr_help_cache.hints[hint_id] = err_stat.get('_hint','')
  else:
    ctxt.append(attr_help(module,data_name))

  log.error(
    text=f'{path} must be {expected}',
    category=log.IncorrectValue if '_value' in err_stat else log.IncorrectType,
    module=module or 'topology',
    more_hints=ctxt)
  return

#
# Get attribute help -- return 'use netlab show attributes XYZ' help message
#

def attr_help(module: typing.Optional[str], data_name: typing.Optional[str]) -> str:
  global _attr_help_cache

  if data_name is None or module is None:             # We're missing crucial information, cannot provide any help
    return ''

  if _attr_help_cache is None:                        # Initialize help messages cache if needed
    from ..data import get_empty_box
    _attr_help_cache = get_empty_box()

  topology = global_vars.get_topology()               # Try to get current lab topology
  if not topology:                                    # ... not initialized yet, too bad
    return ''
  
  defaults = topology.defaults                        # Get topology defaults
  attr_list = data_name.lower().split(' ')            # Split data name into its components
  if attr_list[-1] == 'topology':                     # Remove the extraneous 'topology' bit
    attr_list.pop()

  attrs     = defaults.attributes                     # Assume global validation context
  mod_cache = 'global'

  if not attr_list:                                   # Nothing left to guess, get out
    return ''

  if attr_list[0] == module and module in defaults and 'attributes' in defaults[module]:
    attrs = defaults[module].attributes               # Looks like we're within a valid module validation context
    mod_cache = module
    attr_list.pop(0)
  else:
    module = ''                                       # Otherwise assume global context, clear 'module' information

  # Get attribute type (or empty)
  attr_type = attr_list[-1] if attr_list else ''
  if not attr_type in attrs:                          # No such attribute in the current context, display just the context help
    attr_type = ''

  # No need to print out the same help message twice, check the message cache
  #
  if mod_cache in _attr_help_cache and attr_type in _attr_help_cache[mod_cache]:
    return ''

  _attr_help_cache[mod_cache][attr_type] = True       # Remember we were asked to provide this help message
  if not attr_type and not mod_cache:                 # ... but it makes no sense to give extra help if the show command
    return ''                                         # ... won't print the desired attributes

  # Looks like we passed all sanity checks, return (hopefully useful) extra information
  #
  return f"use 'netlab show attributes{' --module '+module if module else ''}" + \
         f"{' ' + attr_type if attr_type else ''}' to display valid attributes"

def check_valid_values(
      path: str,                                        # Path to the value
      expected:  list,                                  # Expected values
      value:     typing.Any,                            # Value we got
      key:       typing.Optional[str] = None,           # Optional key within the object
      context:   dict = {},                             # Optional validation context
      data_name: typing.Optional[str] = None,           # Data name, needed for attribute help
      module:    typing.Optional[str] = None,           # Module name to display in error messages
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
  if '_raw_status' not in context and '_silent' not in context:
    log.error(
      text=f'attribute {path} has invalid value(s): {value}',
      more_hints=[
        f'valid values are: {", ".join(expected)}',
        attr_help(module,data_name)],
      category=log.IncorrectValue,
      module=module or 'topology')

  if context.get('_abort',False):
    raise log.IncorrectValue()
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
  data_name     - Context of the element to check (example: bgp node), used for error messages
  module        - The caller module (used for error messages)
  valid_values  - list of valid values (applicable to all data types)
  create_empty  - Create an empty element if the value is missing
  true_value    - Replace True with another value

Common context arguments:

  _abort        - Throw an exception after printing an error message

Sample use: make sure the 'config' attribute of a node is list

  must_be_list(node,'config',f'nodes.{node.name}')

"""

def get_value_to_check(
      parent: Box,                                      # Parent object
      key: str,                                         # Key within the parent object, may include dots.
      empty_value: typing.Optional[typing.Any] = None,  # Optional value to use when there is no value
      create_empty: typing.Optional[bool] = None,       # Do we need to create an empty value?
      true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_
      false_value: typing.Optional[typing.Any] = None,  # Value to use to replace _false_
      context: dict = {}) -> typing.Any:                # Additional validation context

  value = parent.get(key,None)                          # Try to get the value from the parent object

  if value is None:                                     # No value was found, now what?
    if empty_value is not None:                         # ... is there empty value for this data type?
      if create_empty is None:                          # Empty value is defined, and we'll use it to create an empty object if the caller
        create_empty = True                             # did not specify its preferencehs

      if create_empty:                                  # Now for the real deal
        value = empty_value                             # ... if we should create an empty value do so
        parent[key] = empty_value                       # ... and store it in the parent object
      else:
        if context.get('_abort',False):                 # Empty value was specified, 'create_empty' is False, and there's no actual value
          raise log.IncorrectValue()                    # ... raise an exception if requested

    if not key in parent:                               # We can skip further processing if the key is missing.
      return value

  # Handle boolean-to-data-type conversions if the value is bool and the caller specified true_value
  #
  if isinstance(value,bool):
    if value is True:                                   # Replace True with true_value and move on
      if true_value is not None:
        value = true_value
        parent[key] = value
    else:
      if false_value is None:                           # If there's no false_value pop the bool option and return None
        parent.pop(key,None)
        append_to_list(parent,'_removed_attr',key)
        return None
      else:
        value = false_value                             # ... otherwise set the false value
        parent[key] = value

  return value

"""
post-validation processing

Validator function could return:

* True -- everything is OK
* False -- failed the validation, error message was already printed
* string -- error message
* callable -- a function returning a replacement value
"""

def post_validation(
      value: typing.Any,
      parent: typing.Optional[Box],
      path: str,
      key: typing.Optional[str],
      err_stat: dict,
      data_name: typing.Optional[str] = None,
      module: typing.Optional[str] = None,
      context: dict = {}) -> typing.Any:

  if not err_stat.get('_valid',False):
    if '_raw_status' not in context and '_silent' not in context:
      wrong_type_message(
        path=path,
        key=None if parent is None else key,
        err_stat=err_stat,value=value,
        context=context,
        data_name=data_name,module=module)
    if context.get('_abort',False):
      raise log.IncorrectType()
    return None
  
  if '_transform' in err_stat:
    value = err_stat['_transform'](value)
    if not parent is None:
      parent[key] = value

  return value

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
          parent: typing.Optional[Box],                     # Parent object
          key: str,                                         # Key within the parent object, may include dots.
          path: str,                                        # Path to parent object, used in error messages
##        context: typing.Optional[typing.Any] = None,      # Additional context (use when verifying link values)
          data_name: typing.Optional[str] = None,           # Optional data validation context
          module: typing.Optional[str] = None,              # Module name to display in error messages
          valid_values: typing.Optional[list] = None,       # List of valid values
          create_empty: typing.Optional[bool] = None,       # Do we need to create an empty value?
          true_value: typing.Optional[typing.Any] = None,   # Value to use to replace _true_ (false_values used to replace _false_)
          **kwargs: typing.Any) -> typing.Optional[typing.Any]:

      context: dict = {}                                    # Build validation context
      if kwargs:                                            # Do we have any extra parameters?
        for k in list(kwargs.keys()):                       # Split extra parameters into validation and context parameters
          if k.startswith('_'):                             # ... parameters starting with _ are context parameters
            context[k] = kwargs[k]                          # ... for example, _abort
            kwargs.pop(k,None)

      if parent is None:                                    # No parent => key is the value to check
        value = key
      else:
        value = get_value_to_check(
                  parent=parent,
                  key=key,
                  empty_value=empty_value,
                  create_empty=create_empty,
                  true_value=true_value,
                  false_value=false_value,
                  context=context)
        if not key in parent:
          return value

      status = test_function(value,**kwargs)              # Now call the validator function with the item value
      value = post_validation(
                value=value,
                parent=parent,
                path=path,
                key=key,
                err_stat=status,
                data_name=data_name,
                module=module,
                context=context)
      
      # Finally, check valid values (if specified)
      #
      if valid_values and status.get('_valid',False):
        if not check_valid_values(
                  path=path,
                  key=None if parent is None else key,
                  value=value,
                  expected=valid_values,
                  data_name=data_name,
                  module=module,
                  context=context):
          status['_value'] = 'Invalid value'
          pass

      if '_raw_status' in context:                        # Did the caller request raw status?
        status['value'] = value                           # ... he did, add transformed value to it
        return status                                     # ... and return

      # Otherwise it's a legacy call. Return whatever the final value is (considering empty, true, and transformed values)
      #
      return value

    return execute_test

  return test_wrapper

def register_type(tname: str, validator: typing.Callable) -> None:
  globals()[f'must_be_{tname}'] = validator

"""
Individual data type validators
===============================

Most validators check the instance type and return a string error message

Exceptions:

* List validator returns a transformation function when a scalar could be converted to a list
* Integer validation can include minimum/maximum values
"""

@type_test(false_value=[],empty_value=[])
def must_be_list(value: typing.Any, make_list: bool = False) -> dict:

  def transform_to_list(value: typing.Any) -> list:
    return [ value ]

  if isinstance(value,list):                            # A list is what we want to have ;)
    return { '_valid': True }

  if isinstance(value,(str,int,float,bool)):            # Handle scalar-to-list transformations with a callback function
    return { '_valid': True, '_transform': transform_to_list }

  if make_list:                                         # Optional: force any other value to become a list
    return { '_valid': True, '_transform': transform_to_list }

  return { '_type': 'a scalar or a list' }

@type_test(false_value={},empty_value={})
def must_be_dict(value: typing.Any) -> dict:
  return { '_valid': True } if isinstance(value,dict) else { '_type': 'a dictionary' }

@type_test()
def must_be_string(value: typing.Any) -> dict:
  return { '_valid': True } if isinstance(value,str) else { '_type': 'a string' }

@type_test()
def must_be_str(value: typing.Any) -> dict:
  return { '_valid': True } if isinstance(value,str) else { '_type': 'a string' }

@type_test()
def must_be_id(value: typing.Any, max_length: typing.Union[int,str] = 16) -> dict:
  id_length = resolve_const_value(max_length,16)
  if not isinstance(id_length,int):
    log.fatal(f'Internal failure in must_be_id: max_length {max_length} did not resolve into int')

  match_str = f'[a-zA-Z_][a-zA-Z0-9_-]{{0,{id_length - 1}}}'
#  print(f'must_be_id: v={value} m={match_str}')
  if not isinstance(value,str) or not re.fullmatch(match_str,value):
    return {
      '_valid': False,
      '_type' : f'a {id_length}-character identifier',
      '_help' : f'a string starting with a letter or an underscore and containing up to {id_length} letters, numbers, or underscores'
    }

  return { '_valid': True } 

def check_int_type(
      value: typing.Any,
      min_value:  typing.Optional[int] = None,          # Minimum value
      max_value:  typing.Optional[int] = None,          # Maximum value
                ) -> dict:
  if not isinstance(value,int):                         # value must be an int
    return { '_type': 'an integer' }

  if isinstance(value,bool):                            # but not a bool
    return { '_value': 'a true integer (not a bool)' }

  if isinstance(min_value,int) and isinstance(max_value,int):
    if value < min_value or value > max_value:
      return { '_value': f'an integer between {min_value} and {max_value}' }
  elif isinstance(min_value,int):
    if value < min_value:
      return { '_value': f'an integer larger or equal to {min_value}' }
  elif isinstance(max_value,int):
    if value > max_value:
      return { '_value': f'an integer less than or equal to {max_value}' }

  return { '_valid': True } 

@type_test()
def must_be_int(
      value: typing.Any,
      min_value:  typing.Optional[int] = None,          # Minimum value
      max_value:  typing.Optional[int] = None,          # Maximum value
                ) -> dict:

  def transform_to_int(value: typing.Any) -> int:
    return int(value)

  if isinstance(value,str):                             # Try to convert STR to INT
    try:
      transform_to_int(value)
      return { '_valid': True, '_transform': transform_to_int }
    except:
      pass

  return(check_int_type(value,min_value,max_value))

@type_test(false_value=False)
def must_be_bool(value: typing.Any) -> dict:

  def transform_to_bool(value: typing.Any) -> bool:
    if value == 'True' or value == 'true':
      return True

    if value == 'False' or value == 'false':
      return False 

    raise ValueError('invalid boolean literal -- use true or false')

  if isinstance(value,str):                             # Try to convert STR to INT
    try:
      transform_to_bool(value)
      return { '_valid': True, '_transform': transform_to_bool }
    except:
      pass

  return { '_valid': True } if isinstance(value,bool) else { '_type': 'a boolean' }

@type_test(false_value=False)
def must_be_bool_false(value: typing.Any) -> dict:

  return { '_valid': True } if value is False else { '_type': 'False' }

@type_test()
def must_be_asn2(value: typing.Any) -> dict:                          # 2-octet ASN (in case we need it somewhere)
  err = 'an AS number (integer between 1 and 65535)'
  if not isinstance(value,int) or isinstance(value,bool):             # value must be an int
    return { '_type': err }

  if value < 0 or value > 65535:
    return { '_value': err }

  return { '_valid': True }

def transform_asdot(value: str) -> int:
  asv = 0
  for asp in value.split('.'):
    asv = 65536 * asv + int(asp)

  return asv

_ASN_help = 'an integer between 1 and 4294967295, optionally written as asdot string N.N where N <= 65535'

def asdot_parsing(value: str) -> dict:
  err = 'a 4-octet AS number'
  global _ASN_help

  as_parts = value.split('.')
  asv = 0
  if len(as_parts) > 2:
    return { '_type': f'{err} with two parts when using as.dot notation' }

  for asn in as_parts:
    try:
      asp = int(asn)
    except:
      return { '_type': f'{err} with each part of as.dot string being an integer' }
    if asp < 0 or asp > 65535:
      return { '_value': f'{err} with each part of as.dot string being a 2-octet value' }

    asv = 65536 * asv + asp

  if asv <= 0 or asv >= 2**32:
    return { '_value': f'{err} -- specified value is out of bounds' }
  
  return { '_valid': True, '_transform': transform_asdot }

@type_test()
def must_be_asn(value: typing.Any) -> dict:
  err = 'a 4-octet AS number'
  global _ASN_help

  if isinstance(value,str):
    return asdot_parsing(value)

  if not isinstance(value,int) or isinstance(value,bool):             # value must be an int
    return { '_type': err, '_help': _ASN_help }

  if value < 0 or value > 4294967295:
    return { '_value': f'{err} -- an integer between 1 and 4294967295' }

  return { '_valid': True }

def transform_named_prefix(value: str) -> str:
    topology = global_vars.get_topology()
    return '' if topology is None else topology.get('prefix',{})[value]

def check_named_prefix(value: str) -> typing.Optional[dict]:
  topology = global_vars.get_topology()
  if topology is not None:
    from ..augment import addressing
    pfxs = topology.get('prefix',{})
    if value in pfxs:
      addressing.evaluate_named_prefix(topology,value)
      return { '_valid': True, '_transform': transform_named_prefix }
  return None

"""
Common IP address validation functionality. Both tests recognize these use cases:

* 'interface' -- an IP prefix that can be used on an interface.
  Allows int (subnet offset) and bool (unnumbered/LLA)
* 'host_prefix' -- an IP address with a prefix length. A subset of 'interface'.
* 'address' -- a pure IP address. Typical use case: next hops for static routes
* 'id' -- identifier that can be an IP address or an int
* 'subnet_prefix' -- an IP prefix that can be used on a subnet, including bool (unnum/LLA).
  Host bits must be zero, and it cannot be in the multicast range.
* 'prefix' -- any IP prefix, including multicast prefixes. Use case: prefix lists

Valid types per use case:

Use case      | str (w/) | str (no/) | bool | int |
--------------+----------+-----------+------+-----+
address       |          |    OK     |      |     |
prefix        |    OK    |           |      |     |
host_prefix   |    OK    |           |      |     |
interface     |    OK    |    OK     |  OK  | OK  |
subnet_prefix |    OK    |           |  OK  |     |
id            |          |    OK     |      | OK  |
--------------+----------+-----------+------+-----+

Furthermore, we can use 'named' prefixes in some scenarios.
"""

RESERVED_PREFIXES: typing.Dict[str,dict] = {
  'IPv4': {
    'local':     ipaddress.IPv4Network('0.0.0.0/8'),
    'loopback':  ipaddress.IPv4Network('127.0.0.0/8'),
    'multicast': ipaddress.IPv4Network('224.0.0.0/4')
  },
  'IPv6': {
    'loopback':  ipaddress.IPv6Network('::1/128'),
    'multicast': ipaddress.IPv6Network('ff00::/8')
  }
}

def common_addr_parse(
      value: typing.Any,
      use: str,
      named: bool,
      af: str,
      net_parse: typing.Callable,
      addr_parse: typing.Callable,
      xform_int: typing.Optional[typing.Callable] = None,
      xform_pfx: typing.Optional[typing.Callable] = None) -> dict:

  global RESERVED_PREFIXES

  def check_int_value(value: int, xform_int: typing.Optional[typing.Callable]) -> dict:
    if value < 0 or value > 2**32-1:
      return { '_value': f'an {af} address or an integer between 0 and 2**32' }
    else:
      if xform_int is not None:
        return { '_valid': True, '_transform': xform_int }
      else:
        return { '_valid': True }

  def check_reserved_range(
        ranges: dict,
        p_addr: typing.Any) -> typing.Optional[str]:
    for k,v in ranges.items():
      if v.overlaps(p_addr):
        return k

    return None

  if isinstance(value,bool):                      # bool values are valid only on interfaces and subnets
    if use not in ('interface','subnet_prefix'):
      return { '_value' : f'an {af} address (boolean value is valid only on an interface)' }
    else:
      return { '_valid': True }

  if isinstance(value,int):                       # integer values are valid only as interface offsts or IDs (OSPF area)
    if use == 'id' and af == 'IPv4':
      return check_int_value(value,xform_int)
    if use != 'interface':
      return { '_value': f'an {af} address or prefix (integer value is only valid as interface offset or a 32-bit ID)' }
    return check_int_value(value,None)

  if not isinstance(value,str):
    return { '_type': f'{af} prefix' if 'prefix' in use else f'{af} address' }

  if named and xform_pfx is not None:             # Check whether we can use a named prefix
    topology = global_vars.get_topology()
    if topology is not None:
      from ..augment import addressing
      pfxs = topology.get('prefix',{})
      if value in pfxs:
        addressing.evaluate_named_prefix(topology,value)
        if 'ipv4' in pfxs[value]:
          return { '_valid': True, '_transform': xform_pfx }

  if use in ['id','address'] or (use in ['interface'] and '/' not in value):
    try:
      p_addr = addr_parse(value)
    except Exception as Ex:
      return { '_value': f'{af} address ({Ex})' }

    return { '_valid': True }
  else:
    try:
      p_addr = net_parse(value,strict=use not in ['interface','host_prefix'])
    except Exception as Ex:
      return { '_value': f'{af} prefix ({Ex})' }

  if use not in ['prefix','id']:
    r_hit = check_reserved_range(RESERVED_PREFIXES[af],p_addr)
    if r_hit:
      return {'_value': f'{af} {"prefix" if "prefix" in use else "address"}'+
                        f' outside of reserved ranges ({value} is in {r_hit} range)'}

  return { '_valid': True }

'''
IPv4 validation -- use the common code, allowing int values and named prefixes
'''
@type_test(false_value=False)
def must_be_ipv4(value: typing.Any, use: str, named: bool = False) -> dict:

  def transform_to_ipaddr(value: int) -> str:
    return str(ipaddress.IPv4Address(value))

  def prefix_to_ipv4(value: str) -> str:
    topology = global_vars.get_topology()
    return '' if topology is None else topology.get('prefix',{})[value].ipv4

  return common_addr_parse(
            value=value,use=use,named=named,af='IPv4',
            net_parse=ipaddress.IPv4Network,
            addr_parse=ipaddress.IPv4Address,
            xform_int=transform_to_ipaddr,
            xform_pfx=prefix_to_ipv4)

'''
IPv6 validation -- use the common code, but without int values or named prefixes
'''
@type_test(false_value=False)
def must_be_ipv6(value: typing.Any, use: str) -> dict:
  return common_addr_parse(
            value=value,use=use,named=False,af='IPv6',
            net_parse=ipaddress.IPv6Network,
            addr_parse=ipaddress.IPv6Address)

@type_test()
def must_be_prefix_str(value: typing.Any) -> dict:

  def transform_to_ipv4(value: typing.Any) -> dict:
    return { 'ipv4': value }

  def transform_to_ipv6(value: typing.Any) -> dict:
    return { 'ipv6': value }

  if not isinstance(value,str):
    return { '_type': 'IPv4 or IPv6 prefix' }

  try:
    parse = ipaddress.ip_network(value)                              # now let's check if we have a valid prefix
  except Exception as ex:
    return check_named_prefix(value) or { '_value': f"IPv4, IPv6, or named prefix" }

  if isinstance(parse,ipaddress.IPv4Network):
    return { '_valid': True, '_transform': transform_to_ipv4 }
  else:
    return { '_valid': True, '_transform': transform_to_ipv6 }

@type_test()
def must_be_named_pfx(value: typing.Any) -> dict:
  topology = global_vars.get_topology()
  if isinstance(value,str):
    if topology is not None and value in topology.get('prefix',{}):
      return { '_valid': True }

    return { '_value': f'a name of a (named) prefix (found {value})' }

  return { '_type': 'named prefix' }

@type_test()
def must_be_addr_pool(value: typing.Any) -> dict:
  topology = global_vars.get_topology()
  if isinstance(value,str):
    if topology is not None:
      if value in topology.get('addressing',{}) or value in topology.defaults.addressing:
        return { '_valid': True }

    return { '_value': f'a name of an addressing pool (found {value})' }

  return { '_type': 'addressing pool' }

@type_test()
def must_be_mac(value: typing.Any) -> dict:
  if not isinstance(value,str):
    return {'_type': 'MAC address' }

  try:
    parse = netaddr.EUI(value)                                        # now let's check if we have a MAC address

    if int(parse) & 0x010000000000:                                   # Check if the multicast bit is set
      return { '_value': "Unicast MAC address" }
  except Exception as ex:
    return { '_value': "MAC address" }

  return { '_valid': True }

@type_test()
def must_be_net(value: typing.Any) -> dict:
  if not isinstance(value,str):
    return { '_type': 'IS-IS NET/NSAP' }

  if not re.fullmatch('[0-9a-f.]+',value):
    return { '_value': 'IS-IS NET/NSAP containing hexadecimal digits or dots' }

  if len(value.replace('.','')) % 2 != 0:
    return { '_value': 'IS-IS NET/NSAP containing even number of hexadecimal digits' }

  return { '_valid': True }

@type_test()
def must_be_rd(value: typing.Any) -> dict:
  if isinstance(value,int) or value is None:                          # Accept RD/RT offets and trust the modules to do the right thing
    return { '_valid': True }                                         # Also: RD set to None can be used to prevent global-to-node RD inheritance

  if not isinstance(value,str):                                       # Otherwise it must be a string
    return { '_type': "route distinguisher" }

  try:
    (rdt,rdi) = value.split(':')
  except Exception as ex:
    return { '_value': "route distinguisher in asn:id or ip:id format" }

  try:
    rdi_parsed = int(rdi)
  except Exception as ex:
    return { '_value': "an RD in asn:id or ip:id format where id is an integer value" }

  try:
    rdt_parsed = int(rdt)
  except Exception as ex:
    try:
      ipaddress.IPv4Address(rdt)
    except Exception as ex:
      return { '_value': "an RD in asn:id or ip:id format where asn is an integer or ip is an IPv4 address" }

  return { '_valid': True }


@type_test()
def must_be_device(value: typing.Any) -> dict:
  from .validate import list_of_devices

  status = {
    '_type':    "device",
    '_hint_id': "devices",
    '_hint':    "Use 'netlab show devices' to display a list of valid devices"
  }

  if not isinstance(value,str):                                       # Otherwise it must be a string
    return status

  if not value in list_of_devices:
    status['_value'] = f'known device type identifier (got {value})'
    return status

  return { '_valid': True }

@type_test()
def must_be_node_id(value: typing.Any) -> dict:
  if not isinstance(value,str):                                       # Otherwise it must be a string
    return { '_type': 'valid node name (a string)' }
  
  topology = global_vars.get_topology()               # Try to get current lab topology
  if topology is None:                                # pragma: no-cover
    log.fatal('Calling node_id validation before the topology has been initialized')

  if value not in topology.nodes:  
    return {
      '_type':    "node",
      '_value':   f"valid node name (found {value})",
      '_hint_id': "nodes",
      '_hint':    "Valid node names are "+", ".join(list(topology.nodes))
    }
  
  return { '_valid': True }

@type_test()
def must_be_r_proto(value: typing.Any) -> dict:
  if not isinstance(value,str):
    return { '_type': 'routing protocol (a string)' }

  rp_list = global_vars.get_const('routing_protocols',['connected'])
  if value not in rp_list:
    return {
      '_type': "routing protocol",
      '_hint': f"Valid values are {','.join(rp_list)}"
    }

  return { '_valid': True }
