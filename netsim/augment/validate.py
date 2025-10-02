#
# Process validation data structures
#
import typing

from box import Box

from ..data.global_vars import get_const
from ..utils import log

'''
lookup_wait_time: convert wait time to integer
'''
def lookup_wait_time(v_entry: Box, topology: Box) -> None:
  if not 'wait' in v_entry:
    return

  if isinstance(v_entry.wait,int):
    return

  w_const = v_entry.wait
  v_entry.wait = -1
  w_time = get_const(f'validate.{w_const}')
  if isinstance(w_time,int):
    v_entry.wait = w_time

  d_set = { node.device for node in topology.nodes.values() }
  d_set = d_set.union({ p_device for device in d_set
                          for p_device in topology.defaults.devices[device].get('_parents',[]) })
  for device in d_set:
    dw_time = get_const(f'validate.{device}.{w_const}')
    if isinstance(dw_time,int) and dw_time > v_entry.wait:
      log.info(
        f"Adjusted wait time in '{v_entry.name}' validation test to {dw_time}",
        module=device)
      v_entry.wait = dw_time

  if v_entry.wait < 0:
    log.error(
      f'Wait time {v_entry.wait} specified in validation entry {v_entry.name} is not a validation constant',
      more_hints='Define validation constants in defaults.const.validate',
      category=log.IncorrectValue,
      module='validation')

'''
validate_test_entry: Check if the test makes sense

* Every test should have 'wait', 'show', or 'exec' option
* Tests with 'show' option should have 'valid' option
* Tests with 'valid' option should have 'show' or 'exec' option
'''

def validate_test_entry(v_entry: Box, topology: Box) -> bool:
  kw_set = set(v_entry.keys())
  action_set = set(['show','exec','config','wait','plugin','suzieq'])
  if not kw_set & action_set:                           # Test should have at least one of show/exec/wait
    log.error(
          f'Test {v_entry.name} should have wait, show, exec, config, plugin, or suzieq option',
          category=log.MissingValue,
          module='validation')
    return False

  lookup_wait_time(v_entry,topology)
  if isinstance(v_entry.get('suzieq',{}),str):          # Make sure suzieq entry (if exists) is a dictionary
    v_entry.suzieq = { 'show': v_entry.suzieq }

  if isinstance(v_entry.get('config',{}),str):          # Make sure config entry (if exists) is a dictionary
    v_entry.config = { 'template': v_entry.config }

  # Each validation test should have exactly one action, the only exception is 'exec' and 'show
  # which can be used together to deal with devices that cannot produce JSON printout
  #
  x_kw = [ kw for kw in ('show','exec','config','plugin','suzieq') if kw in v_entry ]
  if len(x_kw) > 1:                                     # We have more than one action. Now take away show/exec
    r_kw = [ kw for kw in x_kw if kw not in ('show','exec') ]
    if r_kw:                                            # If there's something left, we have a problem
      log.error(
            f'You cannot use {",".join(x_kw)} in test {v_entry.name}. Use only one action per test',
            category=log.IncorrectValue,
            module='validation')
      return False

  if not kw_set & set(['suzieq','wait']) and not 'nodes' in v_entry:
    log.error(
          f'Test {v_entry.name} must specify the nodes to execute the test on',
          hint='nodes',
          category=log.IncorrectValue,
          module='validation')
    return False

  if 'show' in v_entry and 'valid' not in v_entry:      # A test with 'show' must also have 'valid'
    log.error(
          f'Test {v_entry.name} has a "show" option but no "valid" option',
          category=log.MissingValue,
          hint='show',
          module='validation')
    return False

  if 'valid' not in v_entry:                            # A test does not have 'valid' option, no further validation needed
    return True

  if not kw_set & set(['show','exec','suzieq']):        # If we know how to get results to validate, we're OK
    log.error(
          f'Test {v_entry.name} has a "valid" option but no action that would generate data to check',
          hint='valid',
          category=log.MissingValue,
          module='validation')                          # OOPS, we have no action that would produce a result to validate
    return False

  return True

'''
calculate_device_support: Figure out which devices are supported by the current validation test

If the validation entry includes 'devices' we're good to go -- hopefully the topology creator
knows what he's doing. Otherwise, we'll take a union of devices mentioned in 'show' and 'exec'
entries and do an intersectiion with the 'valid' entry
'''

def calculate_device_support(v_entry: Box, topology: Box) -> bool:
  if 'show' not in v_entry and 'exec' not in v_entry:
    return True

  if 'devices' in v_entry:                            # Validation entry has an explicit list of supported devices
    return True                                       # ... nothing to do here
  
  d_set: typing.Set = set()                           # We'll try to figure out what devices are supported
  for kw in ('show','exec'):                          # Iterate over the action keywords
    if kw not in v_entry:                             # ... keyword not present, move on
      continue
    if isinstance(v_entry[kw],str):                   # ... keyword is a useless string, move on
      continue
    d_set = d_set | set(v_entry[kw].keys())           # Found a dictionary, extract devices mentioned in it

  if 'valid' in v_entry:                              # If we happen to have the validation expression
    if isinstance(v_entry.valid,dict):                # ... and it is a dictionary
      d_set = d_set & set(v_entry.valid.keys())       # ... then consider only devices with an action and a validation

  v_entry.devices = sorted(list(d_set))               # Sort devices to have consistent test results ;)
  if not v_entry.devices:                             # ... and report an error if we have a useless test
    log.error(
      f'Validation test {v_entry.name} does not include any valid device',
      category=log.MissingValue,
      module='validation')
    return False
  
  return True

'''
Process validation data structure

Lab validation is specified as a dictionary of entries that have to be executed
in the specified order. As the generation of YAML snapshot file (where 'netlab validate'
gets its data) reorders the dictionary keys, we turn the dictionary into a list as
the last step in the lab validation data processing.
'''
def process_validation(topology: Box) -> None:
  if 'validate' not in topology:                            # No lab validation, nothing to do ;)
    return

  for t_name,v_entry in topology.validate.items():          # Iterate over test dictionary
    v_entry.name = t_name                                   # Copy test name into test entry
    if not validate_test_entry(v_entry,topology):           # ... check whether the test makes sense
      continue

    calculate_device_support(v_entry,topology)              # ... and calculate supported devices

  topology.validate = list(topology.validate.values())      # Finally, turn validation dictionary into a list
