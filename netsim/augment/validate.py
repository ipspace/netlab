#
# Process validation data structures
#
from box import Box

from ..utils import strings,log
from .. import data

import typing

'''
calculate_device_support: Figure out which devices are supported by the current validation test

If the validation entry includes 'devices' we're good to go -- hopefully the topology creator
knows what he's doing. Otherwise, we'll take a union of devices mentioned in 'show' and 'exec'
entries and do an intersectiion with the 'valid' entry
'''

def calculate_device_support(v_entry: Box, topology: Box) -> bool:
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
    calculate_device_support(v_entry,topology)              # ... and calculate supported devices

  topology.validate = list(topology.validate.values())      # Finally, turn validation dictionary into a list
