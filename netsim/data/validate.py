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

"""
get_valid_attributes

Given an attribute dictionary, list of valid attribute categories, and extra attributes, return a list
of valid attributes, or a string (type name) if the first attribute source in the list is a string
"""

def get_valid_attributes(
      attributes: Box,                                  # Where to get valid attributes from
      attr_list: typing.List[str],                      # List of valid attributes (example: ['node'] or ['link','interface'])
      extra_attributes: typing.Optional[list] = None    # List of dynamic attributes (needed to validate node provider settings)
        ) -> typing.Union[str,list]:

  valid = []
  for idx,atlist in enumerate(attr_list):               # Build a list of all valid (global) attributes for the object
    add_attr = attributes.get(atlist,[])                # Attributes to add to the list
    if isinstance(add_attr,list):                       # Are we dealing with a fixed-type attribute?
      no_propagate = f'{atlist}_no_propagate'           # No-propagate list excluded only for non-first attribute category
      if idx and no_propagate in attributes:
        add_attr = [ k for k in add_attr if not k in attributes[no_propagate] ]
      valid.extend(add_attr)                            # ... nope, add to list of attributes and move on

      internal_atlist = f'{atlist}_internal'            # Internal object attributes (used by links)
      if internal_atlist in attributes:                 # Add internal attributes if they exist
        valid.extend(attributes[internal_atlist])
      continue

    if valid:                                           # Have we already collected something?
      common.fatal(
        f'Internal error trying to build list of attributes for {attr_list} -- unexpected value at {atlist}\n' +
        f'... attributes: {attributes}')
      return []                                         # ... bad karma, inconsistent validation requirements

    if not isinstance(add_attr,str):                    # Looking good so far, but the thing we got that's not a list should be a string
      common.fatal(
        f'Internal error: Expected string or list for {atlist} attributes\n' +
        f'... attributes: {attributes}')
      return []                                         # ... dang, someone messed up. Abort, abort, abort...

    return add_attr

  if not extra_attributes is None:                      # Extend the attribute list with dynamic attributes
    valid.extend(extra_attributes)

  return valid

"""
build_module_extra_attributes -- build a list of extra attributes defined by modules

Some modules (vlan, vrf) define extra attributes (vlans, vrfs). While those attributes get added to the correct
attribute lists during module initialization phase, it's good to know what hasn't been enabled if those attributes
are not valid, so we're building a reverse lookup list from defaults._module_.attributes.extra lists
"""

def build_module_extra_attributes(topology: Box) -> None:
  global_attr = topology.defaults.attributes            # Shortcut to global attribute list (where 'extra' list will be added)
  # Iterate over all modules
  for m in topology.defaults.keys():                    # Iterate over all default settings
    if not 'supported_on' in topology.defaults[m]:      # ... not a module, move on
      continue
    mod_attr = topology.defaults[m].attributes          # A convenient shortcut to current module attributes to keep code simple
    if not 'extra' in mod_attr:                         # No extra attributes for this module, move on
      continue

    for a_cat,a_list in mod_attr.extra.items():         # Now iterate over all attribute categories defined by this module
      for attr in a_list:                               # ... and for every entry in that list
        global_attr.extra[a_cat][attr] = m              # ... add a pointer back to the module

"""
get_extra_module_attributes -- return a dictionary of extra module attributes relevant to current validation context
"""
def get_extra_module_attributes(attributes : Box,attr_list: typing.List[str]) -> dict:
  return { 
    attr:mod for a_cat,a_extra in attributes.extra.items() \
               if a_cat in attr_list \
                 for attr,mod in a_extra.items() }

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
validate_attributes -- validate object attributes

Iterate over all keys in the 'data' dictionary and check whether they're valid global attributes
or module names. For module attributes, iterate over all valid module attributes

Returns the original data or None transformed into an empty dictionary
"""

list_of_modules: typing.List[str] = []

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
      extra_attributes: typing.Optional[list] = None    # List of dynamic attributes (needed to validate node provider settings)
        ) -> typing.Any: 

  #
  # Part 1: set up default values
  #
  global list_of_modules

  if attributes is None:
    attributes = topology.defaults.attributes

  if not 'extra' in topology.defaults.attributes:
    build_module_extra_attributes(topology)

  if module_source is None:
    module_source = data_path

  if not list_of_modules:
    list_of_modules = [ m for m in topology.defaults.keys() if 'supported_on' in topology.defaults[m] ]

  if common.debug_active('validate'):
    print(f'validate {data_path} against {attr_list} attributes + {modules} modules from {module_source}')

  #
  # Part 2: Build the list of valid attributes
  #
  # It could be that the list of attributes tells us data should be of certain type
  # Deal with that as well (although in an awkward way that should be improved)
  #
  valid = get_valid_attributes(attributes,attr_list,extra_attributes)
  extra_module_attr = get_extra_module_attributes(topology.defaults.attributes,attr_list)
  if isinstance(valid,str):                   # Validate data that is not a dictionary
    data_type = type(data).__name__
    if data_type == valid:                    # OK, we have a match
      return data

    common.error(
      f'{data_path} should be {valid}, found {data_type} instead',
      common.IncorrectType,
      'validate')
    return data

  #
  # Now that we know the valid attributes are a list, add extra attributes from enabled modules
  #

  if not modules is None:
    valid.extend([ attr for attr,mod in extra_module_attr.items() if mod in modules ])

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
    common.error(
      f'Cannot validate attributes in {data_path} -- that should have been a dictionary, found {type(data).__name__}',
      common.IncorrectType,
      'validate')
    return

  for k in data.keys():
    if k.startswith('_'):                               # Skip internal attributes
      continue

    if k in valid:
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
        modules=[],                                     # No extra modules to add
        module=k,                                       # Error message generated by the module
        attributes=topology.defaults[k].attributes)     # Use module attributes

      if data[k] is None:                               # If we're trying to validate module value None...
        data[k] = fixed_data                            # ... replace it with whatever recursive call returned (might be a dict)

      continue

    if k in list_of_modules and not modules is None:
      common.error(
        f"{data_path} uses an attribute from module {k} which is not enabled in {module_source}",
        common.IncorrectAttr,
        module)
      continue

    if k in extra_module_attr and not modules is None:
      common.error(
        f"Attribute '{k}' used in {data_path} is defined by module {extra_module_attr[k]} which is not enabled",
        common.IncorrectAttr,
        module)
      continue

    common.error(
      f"Invalid {data_name} attribute '{k}' found in {data_path}",
      common.IncorrectAttr,
      module)
