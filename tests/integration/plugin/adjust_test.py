"""
The plugin goes through the '_adjust' list, checks whether the 'features'
are supported on the specified 'nodes' and if not:

* Removes everything listed in the 'remove' list
* Replaces everything listed in the 'replace' list (key/value pairs)
* Adds a 'warning'
"""

import typing

from box import Box

from netsim.augment import devices
from netsim.utils import log, strings


def make_a_list(x: typing.Any) -> list:
  return x if isinstance(x,list) else [ x ]

def get_a_list(x: Box, k: str) -> list:
  return make_a_list(x.get(k,[]))

def check_feature(f_check: typing.Any, node: Box, n_features: Box) -> typing.Optional[bool]:
  if isinstance(f_check,Box):
    f_name = f_check.get('key')
    f_x_value = f_check.get('value')
  else:
    f_name = str(f_check)
    f_x_value = None

  f_value = n_features.get(f_name,None)
  if isinstance(f_value,Box):                   # Skip features that have more-specific bits
    return None

  if f_x_value is None:                         # No expected value?
    return bool(f_value)                        # Return the truthiness of the feature value

  if f_value == f_x_value:                      # Matching the expected value?
    return True                                 # ... perfect!

  if isinstance(f_value,list) and f_x_value in f_value:
    return True                                 # Also OK if the expected value is matching a list entry

  return False                                  # Nope, no good

"""
Iterate over list of features that should be present for the test to work.
In some cases, a less-specific feature might have a scalar value, so we have
to support a list of features, and if any of them is set to a truthy scalar
or list value, we're good to go.
"""
def missing_features(a_entry: Box, node: Box, topology: Box) -> bool:
  n_features = devices.get_device_features(node,topology.defaults)
  check_mode = a_entry.get('check_mode','or')
  if check_mode not in ['or','and']:
    log.error(
      f'Invalid check mode {check_mode}',
      module='adjust_test',
      more_data=str(a_entry))
    return False

  for f_check in get_a_list(a_entry,'features'):
    feature_OK = check_feature(f_check,node,n_features)
    log.print_verbose(f'Checking feature {f_check} on {node.name}/{node.device}: {feature_OK}')
    if feature_OK is None:                        # The check did not return a useful result
      continue
    if feature_OK and check_mode == 'or':         # We found a working feature, so nothing is missing
      return False
    if not feature_OK and check_mode == 'and':    # We found a missing feature
      return True

  # If we got to here, either all features are missing (in OR mode) or all features are OK (in AND mode)
  return check_mode == 'or'                       # Return the result corresponding to the check mode

def adjust_topology(a_entry: Box, topology: Box) -> None:
  OK = True
  for n_name in get_a_list(a_entry,'nodes'):      # Iterate over nodes to check
    if n_name not in topology.nodes:              # Skip missing nodes
      continue
    n_data = topology.nodes[n_name]               # Get node data
    if missing_features(a_entry,n_data,topology): # ... and check for missing features
      OK = False                                  # ... oops, we have a mismatch
      break

  if OK:                                          # All good (or no nodes to check)
    return                                        # ... so get out of here

  # The n_name/n_data contain the first node with missing feature(s)
  #
  w_text = a_entry.get('warning','')              # Do we have to add a warning?
  if w_text:                                      # Print the formatted warning
    w_fmt_text = strings.eval_format(w_text,n_data)
    log.warning(text=w_fmt_text,module='adjust_test',once=True)
    if 'validate' in topology:                    # ... and add a warning-only validation test
      topology.validate.f_warning = {
        'wait': 0,
        'level': 'warning',
        'fail': w_fmt_text }

  for af in get_a_list(a_entry,'remove_af'):
    for kw in ('addressing','pools'):
      for pool_name,pool_data in topology.get(kw,{}).items():
        for pfx in (af,f'{af}_pfx'):
          if pfx in pool_data:
            pool_data.pop(pfx)
            log.print_verbose(f'Removing {kw}.{pool_name}.{pfx}')

  for rm_item in get_a_list(a_entry,'remove'):
    log.print_verbose(f'Removing {rm_item}')
    if ":" not in rm_item:
      topology.pop(rm_item,None)
      continue

    (object,item) = rm_item.split(":",1)
    for data in topology.get(object,{}).values():
      data.pop(item,None)

  for rp_item in get_a_list(a_entry,'replace'):
    rp_key = rp_item.get('key',None)
    rp_value = rp_item.get('value',None)
    if rp_key:
      log.print_verbose(f'Replacing {rp_key} with {rp_value}')
      topology.pop(rp_key,None)
      topology[rp_key] = rp_value
    else:
      log.warning(text=f'No replacement key defined in {rp_item}',module='adjust_test')

def pre_transform(topology: Box) -> None:
  for a_entry in topology.get('_adjust',[]):
    adjust_topology(a_entry,topology)
