#
# Data validation routines
#

import typing,typing_extensions
from box import Box
from .. import common
from . import get_from_box,set_dots,get_empty_box,get_box

#
# Import functions from data.types to cope with legacy calls to must_be_something
from .types import must_be_list,must_be_dict,must_be_string,must_be_int,must_be_bool

"""
get_valid_attributes

Given an attribute dictionary, list of valid attribute categories, and extra attributes, return a list
of valid attributes, or a string (type name) if the first attribute source in the list is a string
"""

##### REMOVE AFTER ATTRIBUTE MIGRATION #####
def make_attr_dict(atlist: typing.Union[list,Box]) -> typing.Union[Box]:
  if isinstance(atlist,list):
    return Box({ k: None for k in atlist })

  return atlist

def get_valid_attributes(
      attributes: Box,                                      # Where to get valid attributes from
      attr_list: typing.List[str],                          # List of valid attributes (example: ['node'] or ['link','interface'])
      extra_attributes: typing.Optional[list] = None        # List of dynamic attributes (needed to validate node provider settings)
        ) -> typing.Union[str,Box]:

  valid = get_empty_box()
  for idx,atlist in enumerate(attr_list):                   # Build a list of all valid (global) attributes for the object
    if not atlist in attributes:
      continue
    add_attr = attributes[atlist]                           # Attributes to add to the list

    if isinstance(add_attr,str):                            # Got a specific data type?
      if valid:                                             # Have we already collected something?
        common.fatal(
          f'Internal error trying to build list of attributes for {attr_list} -- unexpected value at {atlist}\n' +
          f'... attributes: {attributes}')
        return ''                                           # ... bad karma, inconsistent validation requirements
      return add_attr

    if not isinstance(add_attr,(Box,list)):
      common.fatal(
        f'Internal error: Expected string or list/dictionary for {atlist} attributes\n' +
        f'... attributes: {attributes}')
      return ''                                             # ... dang, someone messed up. Abort, abort, abort...

    add_attr = make_attr_dict(add_attr)                     # Convert attributes into a dictionary

    no_propagate = f'{atlist}_no_propagate'                 # No-propagate list excluded only for non-first attribute category
    if idx and no_propagate in attributes:
      add_attr = { k:v for k,v in add_attr.items() if not k in attributes[no_propagate] }
    valid += add_attr                                       # ... nope, add to list of attributes and move on

    internal_atlist = f'{atlist}_internal'                  # Internal object attributes (used by links)
    if internal_atlist in attributes:                       # Add internal attributes if they exist
      valid += make_attr_dict(attributes[internal_atlist])

  if not extra_attributes is None:                      # Extend the attribute list with dynamic attributes
    valid += make_attr_dict(extra_attributes)

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
    valid += Box({ attr: None for attr,mod in extra_module_attr.items() if mod in modules })

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
