#
# Data validation routines
#

import typing

from box import Box

from ..utils import log
from . import get_a_list, get_empty_box

# We also need to import the whole data.types module to be able to do validation function lookup
from . import types as _tv

#
# Import functions from data.types to cope with legacy calls to must_be_something
from .types import attr_help

# It's easier to have a few global functions than to pass topology parameter
# around
#
list_of_modules: typing.List[str] = []
list_of_devices: typing.List[str] = []
topo_attributes: typing.Optional[Box] = None
topo_pointer: typing.Optional[Box] = None

"""
get_attribute_namespaces

Given a list of attribute namespaces, iterate through attributes and extend the list
with potential _namespace definitions.
"""

def remove_required_flag(a: Box) -> None:                   # Utility function: recursively remove _required flag
  if '_required' in a:                                      # Remove the flag from current dictionary (if present)
    a.pop('_required',None)

  for v in a.values():                                      # Iterate into child values
    if isinstance(v,Box):                                   # ... and recurse if the child value is a box
      remove_required_flag(v)

def get_attribute_namespaces(
      attributes: Box,                                      # Where to get valid attributes from
      attr_list: typing.List[str]                           # List of attribute namespaces
        ) -> list:

  iterate_list = list(attr_list)                            # Make a copy of the attr list
  return_list = []

  cnt = 0
  while iterate_list:                                       # Repeat until we run out of ideas
    cnt = cnt + 1
    if cnt > 100:                                           # Always nice to detect an infinite loop ;)
      log.fatal('Internal error: Never-ending get_attribute_namespace loop, got {attr_list} / {iterate_list}')

    ns = iterate_list.pop(0)                                # Get the next namespace from the list
    if not ns in attributes and cnt > 1:                    # Not present in the attributes and it's not the primary namespace?
      continue                                              # ... no big deal, ignore it

    if not ns in return_list:                               # Has it already been mentioned?
      return_list.append(ns)                                # ... nope, add it to the list

    if not ns in attributes:                                # Now get out if this namespace has no relevant attributes
      continue                                              # ... or we'll clobber the attr dictionary in the next step

    if '_namespace' in attributes[ns]:                      # Add namespaces to inspect if the current namespace wants that
      iterate_list.extend(get_a_list(attributes[ns]._namespace))

  return return_list

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
        log.fatal(                                          # ... bad karma, inconsistent validation requirements
          f'Internal error trying to build list of attributes for {attr_list} -- unexpected value at {atlist}\n' +
          f'... attributes: {attributes}')

      return add_attr

    if not isinstance(add_attr,Box):
      log.fatal(                                            # ... dang, someone messed up. Abort, abort, abort...
        f'Internal error: Expected dictionary for {atlist} attributes\n' +
        f'... attributes: {attributes}')

    no_propagate = f'{atlist}_no_propagate'                 # No-propagate list excluded only for non-first attribute category
    if idx:                                                 # Special handling for secondary namespaces
      if no_propagate in attributes:                        # Build a reduced dictionary if the secondary namespace has no_propagate list
        add_attr = { k:v for k,v in add_attr.items() if not k in attributes[no_propagate] }
      else:                                                 # Other create a copy of the secondary attributes
        add_attr = add_attr + {}

      remove_required_flag(add_attr)                        # Remove required flags from the secondary namespace attributes

    valid = add_attr + valid                                # ... nope, merge with existing list and move on

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
check_required_keys -- checks that the required keys are present in the data structure
"""

def check_required_keys(data: Box, attributes: Box, path: str,module: str) -> bool:
  result = True
  for k,v in attributes.items():
    if isinstance(v,Box) and '_required' in v and v._required:
      if k in data:
        continue
      log.error(
        f"Mandatory attribute '{path}.{k}' is missing",
        log.MissingValue,
        module)
      result = False

  return result

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
      module_source: str,
      topology: Box,
      attr_list: list,
      attributes: Box,
      enabled_modules: list) -> bool:

  # Assume everything is OK
  return_value = True

  # Validate keys if needed
  if '_keytype' in data_type:
    for k in data.keys():
      if not validate_value(
                value=k,
                data_type=data_type._keytype,
                path=f'NOATTR:{parent_path}.{k}',
                module=module):
        return_value = False

  # Option #1: Validate dictionary where every value is another type
  #
  if '_subtype' in data_type:
    subtype = data_type._subtype
    for k,v in data.items():                      # Iterate over all dictionary values
      if isinstance(subtype,Box) and subtype.get('type',None) == 'error':
        log.error(
          f"Incorrect {data_name} attribute '{k}' in {parent_path}",
          category=log.IncorrectAttr,
          module=module,
          hint=subtype.get('_err_hint',None),
          more_hints=subtype.get('_err_msg',None))
        OK = False
      elif isinstance(data_type._subtype,str) and data_type._subtype in attributes:
        OK = validate_attributes(                 # User defined data type, do full recursive validation including namespaces and modules
          data=v,                                 # Call main validation routines with as many parameters as we can supply
          topology=topology,
          data_path=f'{parent_path}.{k}',
          data_name=f'{subtype}',
          attr_list=[ subtype ],
          modules=enabled_modules,
          module=module,
          module_source=module_source,
          attributes=attributes)
      else:                                       # Simple type that is validated with a must_be_something function
        OK = validate_item(                       # ... call the simpler item validation routine
          parent=data,
          key=k,
          data_type=subtype,
          parent_path=parent_path,
          data_name=data_name,
          module=module,
          module_source=module_source,
          topology=topology,
          attr_list=attr_list,
          attributes=attributes,
          enabled_modules=enabled_modules)

      if OK is False:                             # Aggregate return results into a single boolean value
        return_value = False

  # Option #2: validate a dictionary with specified keys/value types
  #
  if not '_keys' in data_type:                    # If the dictionary does not have the valid keys
    return return_value                           # ... there's nothing further to validate, return what we accumulated so far

  for k in list(data.keys()):                     # Iterate over the elements
    key_type = data_type._keys.get(k,None)
    is_error = isinstance(key_type,Box) and key_type.get('type',None) == 'error'
    if not k in data_type._keys or is_error:       # ... and report elements with invalid name
      #
      # We can get here because the dictionary key is not a valid attribute according to our schema
      # or because we stumbled upon an attribute with an explicit 'error' type
      #
      # In the latter case, we'll try to grab _err_hint and _err_msg attributes and use them
      # (when present) in the error message for further clarification. Please note that we're
      # using a different set of type attributes, to allow a plugin to replace the 'error' type
      # with something useful without inheriting the hints from the 'error' type
      #
      log.error(
        f"Incorrect {data_name} attribute '{k}' in {parent_path}",
        category=log.IncorrectAttr,
        module=module,
        hint=key_type.get('_err_hint',None) if is_error else None,
        more_hints=key_type.get('_err_msg',None) if is_error else None)
      return_value = False
    else:                                         # For valid elements, validate them
      validate_item(
        parent=data,
        key=k,
        data_type=key_type,
        parent_path=parent_path,
        data_name=data_name,
        module=module,
        module_source=module_source,
        topology=topology,
        attr_list=attr_list,
        attributes=attributes,
        enabled_modules=enabled_modules)

  return_value = return_value and check_required_keys(data,data_type._keys,parent_path,module)
  return return_value                             # Return final status

"""
validate_list -- recursively validate a dictionary

Arguments are described in validate_item
"""

def validate_list(
      data: Box,
      data_type: typing.Any,
      parent_path: str,
      data_name: str,
      module: str,
      module_source: str,
      topology: Box,
      attr_list: list,
      attributes: Box,
      enabled_modules: list) -> bool:

  # Assume everything is OK
  return_value = True

  if not '_subtype' in data_type:
    return True

  if log.debug_active('validate'):
    print(f'validate_list {data_name} {parent_path} subtype: {data_type._subtype}')
    print(f'attribute namespaces: {attributes.keys()}')
  for idx,value in enumerate(data):             # Iterate over all list values
    if isinstance(data_type._subtype,str) and data_type._subtype in attributes:
      OK = validate_attributes(                 # User defined data type, do full recursive validation including namespaces and modules
        data=value,
        topology=topology,
        data_path=f'{parent_path}[{idx+1}]',
        data_name=f'{data_type._subtype}',
        attr_list=[ data_type._subtype ],
        modules=enabled_modules,
        module=module,
        module_source=module_source,
        attributes=attributes)
    else:                                       # Simple type that is validated with a must_be_something function
      OK = validate_item(                       # ... call the simpler item validation routine
        parent=None,
        key=value,
        data_type=data_type._subtype,
        parent_path=f'{parent_path}[{idx+1}]',
        data_name=data_name,
        module=module,
        module_source=module_source,
        topology=topology,
        attr_list=attr_list,
        attributes=attributes,
        enabled_modules=enabled_modules)

      if OK is False:                             # Aggregate return results into a single boolean value
        return_value = False
      elif not isinstance(OK,bool):
        data[idx] = OK

  return return_value                             # Return final status

"""
validate_alt_type -- deal with dictionaries that could be specified as something else
"""

def validate_alt_type(data: typing.Any, data_type: Box) -> dict:
  if type(data).__name__ in data_type._alt_types:       # Simple check: is type name in alt types?
    return { '_valid': True }                           # Got it, no need for more complex validation

  v_alt_err: list = []

  for at in data_type._alt_types:                       # Iterate over alt-types
    validation_function = getattr(_tv,f'must_be_{at}',None)
    if not validation_function:                         # Is alt-type a data type with a validation function?
      continue                                          # ... nope, get out of here

    v_result = validation_function(                     # Try to validate
                  parent=None,                          # ... a standalone value
                  key=data,                             # ... specified in this parameter
                  path='',                              # ... no valid path, but we have to supply something 
                  _raw_status=True)                     # ... and return raw validation status
    if v_result.get('_valid',False):
      return v_result
    v_alt_err.append(v_result.get('_value','') or v_result.get('_type',''))

  return { '_alt_types': v_alt_err }                    # No alt data type matched, return the collected error messages


"""
validate_value -- validate a single value (not from an object)
"""

def validate_value(
      value: typing.Any,
      data_type: str,
      path: str,
      module: typing.Optional[str] = None,              # Module name to display in error messages
      **kwargs: typing.Any) -> typing.Any:
  global _bi,_tv

  validation_function = getattr(_tv,f'must_be_{data_type}',None)      # Try to get validation function

  if not validation_function:                                         # No validation function
    log.fatal(f'No validation function for {data_type}')

  return validation_function(
            parent=None,                                # We're validating a standalone value
            key=value,
            path=path,
            module=module,
            **kwargs)                                   # Pass context parameters straight to the validation function

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
check_valid_with: check whether the dictionary has any conflicting attributes

Inputs:
* data to check (should be Box)
* dict data type to check against (could be raw data type or contain _keys)
* path to the object, name of the data, module doing the check
"""
def check_valid_with(
      data: Box,
      data_type: Box,
      path: str,
      data_name: str,
      module: str) -> None:

  if log.debug_active('validate'):
    print(f'check_valid_with {path} {data} against {data_name} {data_type}')

  attr_list = list(data.keys())                             # Get the list of data attributes
  _keys = data_type.get('_keys',data_type)                  # Get the definition of keys
  report_list: typing.List[str] = []                        # List of already-reported incompatibilities

  for attr in attr_list:
    if not isinstance(_keys.get(attr,None),Box):            # Skip invalid attributes or simple types
      continue
    if '_valid_with' not in _keys[attr]:                    # Attribute has no restrictions
      continue
    if attr in report_list:                                 # Incompatibility has already been reported
      continue
    inv_list = [ x for x in attr_list
                  if x != attr and
                     x not in _keys[attr]._valid_with and
                     not x.startswith('_') ]                # Build a list of incompatible attributes
    if inv_list:                                            # ... and report them
      log.error(
        f'Attribute(s) {",".join(inv_list)} cannot be used with attribute {attr} in {path}',
        category=log.IncorrectAttr,
        module=module)
      report_list = report_list + inv_list

"""
validate_item -- validate a single item from an object:

* Return if the data type is None (= not validated)
* Compare data types names if the data type is a string (OK, a bit more complex than that)
* Recursively validate a dictionary

To make matters worse, we cannot pass the item-to-validate directly into the function
but have to invoke it with parent dictionary and key, so we can forward these elements
to "must_be_something" routines.
"""

subtype_validation: dict = {
  'dict': validate_dictionary,
  'list': validate_list
}

PASS_ATTRIBUTES: typing.Final[list] = ['_hint','_help']

def validate_item(
      parent: typing.Optional[Box],
      key: typing.Any,
      data_type: typing.Any,
      parent_path: str,
      data_name: str,
      module: str,
      module_source: str,
      topology: Box,
      attr_list: list,
      attributes: Box,
      enabled_modules: list) -> typing.Any:

  global _bi,_tv,subtype_validation,PASS_ATTRIBUTES

  data = key if parent is None else parent[key]
  if data_type is None:                                               # Trivial case - data type not specified
    return True                                                       # ==> anything goes

  data_type = transform_validation_shortcuts(data_type)

  if log.debug_active('validate'):
    print(f'validate_item {parent_path}.{key} as {data_type}')
    print(f'attribute namespaces: {list(attributes.keys())}')

  # First check the required module(s)
  if '_requires' in data_type:
    rq_module = data_type['_requires']                                # The the list of required modules
    rq_module = rq_module if isinstance(rq_module,list) else [ rq_module ]
    rq_fail = False
    for m in rq_module:
      if not enabled_modules or not m in enabled_modules:
        rq_fail = True                                                # We could exit the loop on first error, but it's nicer
        log.error(                                                    # ... to log all dependency errors
          f"Attribute '{key}' used in {parent_path} requires module {m} "+\
          f"which is not enabled in {module_source.replace('(R)','')}",
          log.IncorrectAttr,
          module)
        
    if rq_fail:                                                       # Attribute failed a dependency test, get out of here
      return False

  # We have to handle a weird corner case: AF (or similar) list that is really meant to be a dictionary
  #
  if isinstance(data,list) and '_list_to_dict' in data_type and parent is not None:
    parent[key] = { k: data_type._list_to_dict for k in data }        # Transform lists into a dictionary (updating parent will make it into a Box)
    data = parent[key]
    data_type = Box(data_type)                                        # and fix datatype definition

  alt_context = {}                                                    # Alt-type context passed to validation functions
  if '_alt_types' in data_type:                                       # Deal with alternate types first
    alt_context = { '_alt_types': data_type._alt_types }
    if type(data).__name__ != data_type.get('type',''):               # Does it make sense to check alternate types?
      alt_result = validate_alt_type(data,data_type)                  # Do we have alt data type (potentially returning modified value)
      if alt_result.get('_valid',False):                              # Did we get a valid alt-type?
        if alt_result.get('value',None):                              # Did it rewrite value?
          if parent is not None:       
            parent[key] = alt_result.get('value')                     # ... it did, don't lose it ;)
          return alt_result.get('value')                              # And return rewritten value
        else:
          return True                                                 # Value not rewritten, return true
      elif alt_result.get('_alt_types',[]):                           # ... alt type check failed, copy expected types
        alt_context['_alt_types'] = alt_result['_alt_types']

  # Copy data type into validation attributes, skipping validation attributes and data type name
  validation_attr = { 
    k:v for k,v in data_type.items() 
      if (not k.startswith('_') and k != 'type') or k in PASS_ATTRIBUTES }
  if '_alt_types' in alt_context:
    validation_attr['_alt_types'] = alt_context['_alt_types']

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

  if parent is not None:                                            # Validation function might have changed the parent value
    data = parent[key]                                              # ... make sure we do the last step using the current value

  if dt_name == 'dict' and isinstance(data_type,Box) and isinstance(data,Box):
    check_valid_with(
      data=data,
      data_type=data_type,
      path=parent_path if parent is None else f'{parent_path}.{key}',
      data_name=data_name,
      module=module)

  if dt_name in subtype_validation:
    return subtype_validation[dt_name](
              data=data,
              data_type=data_type,
              parent_path=parent_path if parent is None else f"{parent_path}.{key}",
              data_name=data_name,
              module=module,
              module_source=module_source,
              topology=topology,
              attr_list=attr_list,
              attributes=attributes,
              enabled_modules=enabled_modules)

  return OK

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
      modules: list = [],                               # List of relevant modules
      module: str = 'attributes',                       # Module generating the error message (default: 'attributes')
      module_source: str = '',                          # Where did we get the list of modules?
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

  if not module_source:
    module_source = data_path

  if log.debug_active('validate'):
    print(f'validate {data_path} against {attr_list} attributes + {modules} modules from {module_source}')

  #
  # Part 2: Build the list of valid attributes
  #
  # It could be that the list of attributes tells us data should be of certain type
  # Deal with that as well (although in an awkward way that should be improved)
  #
  attr_list = get_attribute_namespaces(attributes,attr_list)
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
  # * Check if all the required attributes are present
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

  check_required_keys(data,valid,data_path,module)
  check_valid_with(data,valid,data_path,data_name,module)
  for k in list(data.keys()):
    if any(k.startswith(i) for i in ignored):           # Skip internal attributes
      continue

    if k in valid:                                      # Is this a valid attribute?
      # Now validate the value of the attribute
      validate_item(
        parent=data,
        key=k,
        data_type=valid[k],
        parent_path=data_path,
        data_name=data_name,
        module=module,
        module_source=module_source,
        enabled_modules=modules,
        topology=topology,
        attr_list=attr_list,
        attributes=attributes)
      continue

    # The attribute is not valid for the base data type, but maybe...
    # Do we have to perform recursive check for module attributes?
    if modules and k in modules and '(R)' not in module_source:
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
        modules=modules,                                # Keep the list of modules for _requires checks
        module_source=f'{module_source}(R)',            # ... but don't consider other modules during module attribute check
        module=k,                                       # Error message generated by the module
        attributes=topology.defaults[k].attributes)     # Use module attributes

      if data[k] is None:                               # If we're trying to validate module value None...
        data[k] = fixed_data                            # ... replace it with whatever recursive call returned (might be a dict)

      continue

    if k in list_of_modules and not '(R)' in module_source:
      log.error(
        f"{data_path} uses an attribute from module {k} which is not enabled in {module_source}",
        log.IncorrectAttr,
        module)
      continue

    log.error(
      text=f"Invalid {data_name} attribute '{k}' found in {data_path}",
      more_hints=[ attr_help(module,data_name) ],
      category=log.IncorrectAttr,
      module=module)

"""
init_validation: initial global variables from current topology
"""
def init_validation(topology: Box) -> None:
  global topo_attributes
  global list_of_modules
  global list_of_devices
  global topo_pointer

  topo_pointer = topology
  topo_attributes = topology.defaults.attributes
  list_of_modules = [ m for m in topology.defaults.keys()
                       if isinstance(topology.defaults[m],Box) and 'supported_on' in topology.defaults[m] ]
  list_of_devices = list(topology.defaults.devices.keys())

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
