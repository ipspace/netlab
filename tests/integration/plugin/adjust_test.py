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

"""
Iterate over list of features that should be present for the test to work.
In some cases, a less-specific feature might have a scalar value, so we have
to support a list of features, and if any of them is set to a truthy scalar
or list value, we're good to go.
"""
def missing_features(a_entry: Box, node: Box, topology: Box) -> bool:
  n_features = devices.get_device_features(node,topology.defaults)
  for f_check in get_a_list(a_entry,'features'):
    if isinstance(f_check,Box):
      f_name = f_check.get('key')
      f_x_value = f_check.get('value')
    else:
      f_name = f_check
      f_x_value = None

    f_value = n_features.get(f_name,None)
    log.print_verbose(f'Checking feature {f_name} on {node.name}/{node.device}, expected: {f_x_value}, got {f_value}')
    if isinstance(f_value,Box):                   # Skip features that have more-specific bits
      continue
    if not f_value:                               # Not a truthy value? Still don't know what to do
      continue

    if f_x_value is None:                         # No expected value?
      return False                                # All good, found a feature that works for us

    if f_value == f_x_value:                      # Matching the expected value?
      return False                                # ... perfect!

    if isinstance(f_value,list) and f_x_value in f_value:
      return False                                # Also OK if the expected value is matching a list entry

  return True                                     # Looks like we're missing all the features

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

  for rm_item in get_a_list(a_entry,'remove'):
    log.print_verbose(f'Removing {rm_item}')
    topology.pop(rm_item,None)

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
