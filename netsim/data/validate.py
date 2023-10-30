#
# Data validation routines
#

import typing
import builtins as _bi
from box import Box
from ..utils import log

#
# Import functions from data.types to cope with legacy calls to must_be_something
from .types import must_be_list,must_be_dict,must_be_string,must_be_int,must_be_bool,attr_help

# We also need to import the whole data.types module to be able to do validation function lookup
from . import types as _tv
from . import get_empty_box

# It's easier to have a few global functions than to pass topology parameter
# around
#
list_of_modules: typing.List[str] = []
topo_attributes: typing.Optional[Box] = None

"""
get_valid_attributes

Given an attribute dictionary, list of valid attribute categories, and extra attributes, return a list
of valid attributes, or a string (type name) if the first attribute source in the list is a string
"""

def get_valid_attributes(
      attributes: Box,                                      # Where to get valid attributes from
      attr_list: typing.List[str]                           # List of valid attributes (example: ['node'] or ['link','interface'])
        ) -> typing.Union[str,Box]:

  valid = get_empty_box()

  for idx,atlist in enumerate(attr_list):                   # Build a list of all valid (global) attributes for the object
    if not atlist in attributes:
      continue
    add_attr = attributes[atlist]                           # Attributes to add to the list

    if isinstance(add_attr,str):                            # Got a specific data type?
      if valid:                                             # Have we already collected something?
        log.fatal(
          f'Internal error trying to build list of attributes for {attr_list} -- unexpected value at {atlist}\n' +
          f'... attributes: {attributes}')
        return ''                                           # ... bad karma, inconsistent validation requirements
      return add_attr

    if not isinstance(add_attr,Box):
      log.fatal(
        f'Internal error: Expected dictionary for {atlist} attributes\n' +
        f'... attributes: {attributes}')
      return ''                                             # ... dang, someone messed up. Abort, abort, abort...

    no_propagate = f'{atlist}_no_propagate'                 # No-propagate list excluded only for non-first attribute category
    if idx and no_propagate in attributes:
      add_attr = { k:v for k,v in add_attr.items() if not k in attributes[no_propagate] }
    valid += add_attr                                       # ... nope, add to list of attributes and move on

    internal_atlist = f'{atlist}_internal'                  # Internal object attributes (used by links)
    if internal_atlist in attributes:                       # Add internal attributes if they exist
      valid += attributes[internal_atlist]

  return valid

"""
validate_module_can_be_false: Check whether module attributes for an object can be 'false'
"""
def validate_module_can_be_false(
      attributes: Box,                                  # Attribute definition
      attr_list: typing.List[str]                       # List of valid attributes (example: ['node'] or ['link','interface'])
        ) -> bool:

  if not 'can_be_false' in attributes:
    return False

  intersect = set(attr_list) & set(attributes.can_be_false)
  return bool(intersect)

"""
validate_dictionary -- recursively validate a dictionary

Arguments are described in validate_item
"""

def validate_dictionary(
      data: Box,
      data_type: typing.Any,
      parent_path: str,
      data_name: str,
      module: str,
      enabled_modules: typing.Optional[list] = []
        ) -> bool:

  OK = True
  for k in data.keys():                                             # Iterate over the elements
    if not k in data_type._keys:                                    # ... and report elements with invalid name
      log.error(
        f'Incorrect {data_name} attribute {k} in {parent_path}',
        log.IncorrectAttr,
        module)
      OK = False
    else:                                                           # For valid elements, validate them
      validate_item(
        parent=data,
        key=k,
        data_type=data_type._keys[k],
        parent_path=parent_path,
        data_name=data_name,
        module=module,
        enabled_modules=enabled_modules)
  return OK

"""
validate_alt_type -- deal with dictionaries that could be specified as something else
"""

def validate_alt_type(data: typing.Any, data_type: Box) -> bool:
  return type(data).__name__ in data_type._alt_types

"""
validate_value -- validate a single value (not from an object)
"""

def validate_value(
      value: typing.Any,
      data_type: str,
      path: str,
      context: typing.Optional[typing.Any] = None,      # Additional context (use when verifying link values)
      module: typing.Optional[str] = None,              # Module name to display in error messages
      abort: bool = False) -> typing.Any:
  global _bi,_tv

  validation_function = getattr(_tv,f'must_be_{data_type}',None)      # Try to get validation function

  if not validation_function:                                         # No validation function
    log.fatal(f'No validation function for {data_type}')

  return validation_function(
            parent=None,                                # We're validating a standalone value
            key=value,
            path=path,
            module=module,
            context=context,
            abort=abort)

"""
transform_validation_shortcuts -- transform str/list/dict type definition shortcuts into structured definitions
"""

def transform_validation_shortcuts(data_type: typing.Any) -> typing.Union[Box,dict]:
  global topo_attributes

  if isinstance(data_type,str):                             # Do we have a user-defined data type?
    if topo_attributes and data_type in topo_attributes:    # User-defined data type has to be in defaults.attributes
      data_type = topo_attributes[data_type]                # ... if that's the case, fetch it and continue processing

  if isinstance(data_type,str):                             # Convert a a simple type with no extra attributes
    return { 'type': data_type }                            # ... into a dummy data type dictionary

  # Validating a dictionary against a dictionary of elements without a specified type
  if isinstance(data_type,Box):
    if not 'type' in data_type:
      data_keys = { k:v for k,v in data_type.items() if not k.startswith('_') }
      data_type = Box({ k:v for k,v in data_type.items() if k.startswith('_') })
      data_type.type = 'dict'
      data_type._keys = data_keys

    return data_type

  if isinstance(data_type,list):                            # Convert list into 'list' datatype with 'valid_values'
    return {
      'type': 'list',
      'valid_values': data_type
    }

  log.fatal(f'Internal validation error: unknown data type {data_type}')

"""
validate_item -- validate a single item from an object:

* Return if the data type is None (= not validated)
* Compare data types names if the data type is a string (OK, a bit more complex than that)
* Recursively validate a dictionary

To make matters worse, we cannot pass the item-to-validate directly into the function
but have to invoke it with parent dictionary and key, so we can forward these elements
to "must_be_something" routines.
"""

def validate_item(
      parent: Box,
      key: str,
      data_type: typing.Any,
      parent_path: str,
      data_name: str,
      module: str,
      enabled_modules: typing.Optional[list] = []) -> typing.Any:
  global _bi,_tv

  data = parent[key]
  if data_type is None:                                               # Trivial case - data type not specified
    return True                                                       # ==> anything goes

  data_type = transform_validation_shortcuts(data_type)

  # First check the required module(s)
  if '_requires' in data_type:
    rq_module = data_type['_requires']                                # The the list of required modules
    rq_module = rq_module if isinstance(rq_module,list) else [ rq_module ]
    rq_fail = False
    for m in rq_module:
      if not enabled_modules or not m in enabled_modules:
        rq_fail = True                                                # We could exit the loop on first error, but it's nicer
        log.error(                                                    # ... to log all dependency errors
          f"Attribute '{key}' used in {parent_path} requires module {m} which is not enabled in this context",
          log.IncorrectAttr,
          module)
        
    if rq_fail:                                                       # Attribute failed a dependency test, get out of here
      return False

  # We have to handle a weird corner case: AF (or similar) list that is really meant to be a dictionary
  #
  if isinstance(data,list) and '_list_to_dict' in data_type:
    parent[key] = { k: data_type._list_to_dict for k in data }        # Transform lists into a dictionary (updating parent will make it into a Box)
    data = parent[key]
    data_type = Box(data_type)                                        # and fix datatype definition

  if '_alt_types' in data_type:                                       # Deal with alternate types first
    if validate_alt_type(data,data_type):
      return True

  # Copy data type into validation attributes, skipping validation attributes and data type name
  validation_attr = { k:v for k,v in data_type.items() if not k.startswith('_') and k != 'type' }

  dt_name = data_type['type']
  validation_function = getattr(_tv,f'must_be_{dt_name}',None)        # Try to get validation function

  if not validation_function:                                         # No validation function
    log.fatal(f'No validation function for {data_type}')

  # We have to validate an item with a validation function
  #
  if dt_name in ('dict','list') and not 'create_empty' in validation_attr:
    validation_attr['create_empty'] = False                           # Do not create empty dictionaries/lists unless told otherwise

  # Now call the validation function and hope for the best ;)
  #
  OK = validation_function(
          parent=parent,                                            # We're validating a single item
          key=key,                                                  # So we're setting the retrieval key to None
          path=parent_path,                                         # Pass the parent path (it will be combined with key anyway)
          data_name=data_name,                                      # Pass name of the data
          module=module,                                            # ... and the module
          **validation_attr)                                        # And any other attributes
  if not OK:
    return OK
  
  if dt_name == 'dict' and '_keys' in data_type:
    return validate_dictionary(
              data=data,
              data_type=data_type,
              parent_path=f"{parent_path}.{key}",
              data_name=data_name,
              module=module,
              enabled_modules=enabled_modules)

  return True

"""
validate_attributes -- validate object attributes

Iterate over all keys in the 'data' dictionary and check whether they're valid global attributes
or module names. For module attributes, iterate over all valid module attributes

Returns the original data or None transformed into an empty dictionary
"""

def validate_attributes(
      data: Box,                                        # Object to validate
      topology: Box,                                    # Pointer to topology
      data_path: str,                                   # Path to the data object (needed in error messages)
      data_name: str,                                   # Name of the object (needed in error messages, example: 'node')
      attr_list: typing.List[str],                      # List of valid attributes (example: ['node'] or ['link','interface'])
      modules: typing.Optional[list] = [],              # List of relevant modules
      module: str = 'attributes',                       # Module generating the error message (default: 'attributes')
      module_source: typing.Optional[str] = None,       # Where did we get the list of modules?
      attributes: typing.Optional[Box] = None,          # Where to get valid attributes from
      extra_attributes: typing.Optional[Box] = None,    # Dynamic attributes (needed to validate provider and tool settings)
      ignored: typing.Optional[list] = ['_']            # Ignored prefixes
        ) -> typing.Any: 

  #
  # Part 1: set up default values
  #
  global list_of_modules
  global topo_attributes

  if attributes is None:
    attributes = topology.defaults.attributes

  if extra_attributes:
    attributes = attributes + extra_attributes

  if not ignored:
    ignored = ['_']

  if not isinstance(attributes,Box):
    log.fatal('Internal error in validate_attributes: attributes is not a Box')
    return None

  if module_source is None:
    module_source = data_path

  if log.debug_active('validate'):
    print(f'validate {data_path} against {attr_list} attributes + {modules} modules from {module_source}')

  #
  # Part 2: Build the list of valid attributes
  #
  # It could be that the list of attributes tells us data should be of certain type
  # Deal with that as well (although in an awkward way that should be improved)
  #
  valid = get_valid_attributes(attributes,attr_list)
  if isinstance(valid,str):                   # Validate data that is not a dictionary
    validate_value(                           # Use standalone value validator
      value=data,
      data_type=valid,
      path=data_path,
      module=module)
    return data

  # Part 3 -- validate attributes
  #
  # * Anything starting with "_" is OK (internal attributes)
  # * Known attributes for object we're checking are OK
  # * Module attributes are OK, but have to be checked recursively
  # * Attributes from modules not used by the current object are NOT OK
  # * Anything else is clearly an error
  #
  if data is None:
    return {}                                           # Can't validate attributes of None, but maybe the caller can fix this
  if not isinstance(data,Box):
    log.error(
      f'Cannot validate attributes in {data_path} -- that should have been a dictionary, found {type(data).__name__}',
      log.IncorrectType,
      'validate')
    return

  for k in data.keys():
    if any(k.startswith(i) for i in ignored):           # Skip internal attributes
      continue

    if k in valid:
      validate_item(
        parent=data,
        key=k,
        data_type=valid[k],
        parent_path=data_path,
        data_name=data_name,
        module=module,
        enabled_modules=modules)
      continue

    if not modules is None and k in modules:            # For module attributes, perform recursive check
      if data[k] is False and validate_module_can_be_false(attributes,attr_list):
        continue                                        # Some objects accept 'attribute: false' syntax (example: links)
      if data[k] is True:
        if set(attr_list) & set(topology.defaults[k].attributes.can_be_true):
          continue
      fixed_data = validate_attributes(
        data=data[k],
        topology=topology,
        data_path=f'{data_path}.{k}',                   # Change 'node' to 'node.bgp'
        data_name=f'{k} {data_name}',                   # Change 'node' to 'bgp node' to be used in 'bgp node attribute...'
        attr_list=attr_list,                            # Not changing the checking context
        modules=None,                                   # Do not consider other modules during module attribute check
        module=k,                                       # Error message generated by the module
        attributes=topology.defaults[k].attributes)     # Use module attributes

      if data[k] is None:                               # If we're trying to validate module value None...
        data[k] = fixed_data                            # ... replace it with whatever recursive call returned (might be a dict)

      continue

    if k in list_of_modules and not modules is None:
      log.error(
        f"{data_path} uses an attribute from module {k} which is not enabled in {module_source}",
        log.IncorrectAttr,
        module)
      continue

    log.error(
      f"Invalid {data_name} attribute '{k}' found in {data_path}"+attr_help(module,data_name),
      log.IncorrectAttr,
      module)

"""
init_validation: initial global variables from current topology
"""
def init_validation(topology: Box) -> None:
  global topo_attributes
  global list_of_modules

  topo_attributes = topology.defaults.attributes
  list_of_modules = [ m for m in topology.defaults.keys() if 'supported_on' in topology.defaults[m] ]

"""
Get object-specific attributes

input: list of attribute types (example: ['providers','tools'])
output: dict of object-specific attributes
"""

def get_object_attributes(object_type_list: typing.List[str], topology: Box) -> Box:
  attrs = get_empty_box()

  for o_type in object_type_list:
    if not o_type in topology.defaults:
      continue

    object_data = topology.defaults[o_type]
    for o_name in object_data.keys():
      if 'attributes' in object_data[o_name]:
        for kw,v in object_data[o_name].attributes.items():
          attrs[kw][o_name] = v
      else:
        for kw in ['node','link','interface']:
          attrs[kw][o_name] = None

  return attrs
