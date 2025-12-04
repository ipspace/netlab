#
# Common validation utility functions
#

import re
import typing

from box import Box, BoxList

from ...utils import log, templates
from . import plugin, report

'''
Get generic or per-device action from a validation entry

* If the validation entry is a string, use that
* If the validation entry is a dictionary, use device-specific item
* If the result of the above is not a string we have a failure, get out
* If the resulting string contains '{{' run it through Jinja2 engine

If we try to get the string to pass to the device from a plugin, then any
plugin evaluation errors indicate something is badly broken, so we log the
error with as much data as feasible... and if the end-user ever sees that
error message, the author of the validation plugin did a lousy job.
'''
def get_entry_value(v_entry: Box, action: str, node: Box, topology: Box) -> typing.Any:
  n_device = node.device
  if action in v_entry:
    value = v_entry[action][n_device] if isinstance(v_entry[action],dict) else v_entry[action]
  elif 'plugin' in v_entry:
    try:
      value = plugin.exec_plugin_function(action,v_entry,node)
    except plugin.PluginEvalError as ex:
      indent = (topology._v_len + 3) if topology else 10
      log.error(
        text=str(ex),
        category=log.IncorrectValue,
        module='validate',
        more_hints=[ f'device: {node.device}, action: {action}', f'plugin expression: {action}_{v_entry.plugin}'],
        indent=indent)
      return None

  if not isinstance(value,str):
    return value
  
  if '{{' in value:
    try:
      node.hostvars = topology.nodes                              # Mimicking Ansible, make other node data available as 'hostvars'
      value = templates.render_template(data=node,j2_text=value)
      node.pop('hostvars',None)                                   # ... but only while evaluating J2 template
    except Exception as ex:
      log.fatal(f'Jinja2 error rendering {value}\n... {ex}')
#    print(f"{action} value for {node.name}: {value}")

  return value  

'''
Get the command to execute on the device in list format

* Use 'get_entry_value' to get the action string or list
* If we got a string, transform it into a list
'''
def get_exec_list(v_entry: Box, action: str, node: Box, topology: Box) -> list:
  v_cmd = get_entry_value(v_entry,action,node,topology)
  if isinstance(v_cmd,list):
    return v_cmd
  elif isinstance(v_cmd,str):
    return v_cmd.split(' ')

  return []

'''
find_test_action -- find something that can be executed on current node

* Try 'show' and 'exec' actions
* If an action value is a string, the user doesn't care about multi-vendor
  setup. Run with whatever the user specified
* If the user specified a multi-vendor setup, try to use the device-specific
  action
* If there's no relevant 'show' or 'exec' action, try the plugin
* If there's no plugin, but we have 'wait' action, return 'wait'
* If everything fails, return None (nothing usable for the current node)
'''
def find_test_action(v_entry: Box, node: Box) -> typing.Optional[str]:
  action_kw_found = False
  for kw in ('show','exec','config','suzieq'):
    if kw not in v_entry:
      continue

    action_kw_found = True
    if kw in ['suzieq','config'] or isinstance(v_entry[kw],(str,int)):
      return kw
    if node.device in v_entry[kw]:
      return kw

  if 'plugin' in v_entry:
    return plugin.find_plugin_action(v_entry,node)

  if 'wait' in v_entry and not action_kw_found:
    return 'wait'

  return None

'''
Try to parse the results returned from a lab device as a JSON

* Cleanup the returned text
* If the cleaned-up text starts with [ we have a list: create a bogus
  wrapper JSON, parse it, and return the inside list
* Otherwise, try to parse the returned text as JSON object

Cleanup part:
* Remove the leading and trailing whitespace
* Find the first [ or { and skip everything in front of it (might be
  an error message mixed with the JSON data)
'''
def parse_JSON(result: str) -> typing.Union[Box,Exception]:
  result = result.strip()
  low_idx = len(result)
  for s_char in ('[','{'):
    p_char = result.find(s_char,0,low_idx)
    if p_char >= 0 and p_char < low_idx:
      low_idx = p_char

  if low_idx < len(result):
    result = result[low_idx:]

  try:
    if result.startswith('['):
      result = f'{{ "rx": {result} }}'
      return Box.from_json(result).rx
    else:
      return Box.from_json(result)
  except Exception as ex:
    return ex

"""
execute_validation_expression: execute the v_entry.valid string in a safe environment with
error/success logging.

Getting the results:

* There is no 'valid' entry: bad, log an error, increase skip count
* Validation expression fails: bad, assume result is False
* Otherwise, the validation function should return True (or some such), False or None

Evaluating the results:

* False: print failure message, increase result count but not pass count
* True: print success message, increase result and pass count
* None: we have no idea what the answer is, skip this test
"""

BUILTINS: dict = {                            # Allowed built-in functions. Extend as needed ;)
  'len': len
}

def execute_validation_expression(
      v_entry: Box,
      node: Box,
      topology: Box,
      result: typing.Union[Box,BoxList],
      verbosity: int,
      report_error: bool,
      report_success: bool = True) -> typing.Optional[bool]:

  global BUILTINS
  from . import TEST_COUNT

  v_test = get_entry_value(v_entry,'valid',node,topology)
  if not v_test:                              # Do we have a validation expression for the current device?
    report.log_info(                          # ... nope, have to skip it
      f'Test results validation not defined for device {node.device} / node {node.name}',
      f_status = 'SKIPPED',
      topology=topology)
    TEST_COUNT.skip += 1
    return None
  else:
    try:                                      # Otherwise try to evaluate the validation expression
      if isinstance(result,BoxList):
        result = Box({'result': result})
      else:
        result.result = result
      result.re = re                          # Give validation expression access to 're' module
      OK = eval(v_test,{ '__builtins__': BUILTINS },result)
      if OK is None:
        OK = False
    except Exception as ex:                   # ... and failure if the evaluation failed
      if verbosity >= 2:
        print(f'... evaluation error: {ex}')
      OK = False

  if not OK or verbosity >= 2:             # Validation expression failed or we're extra verbose
    if verbosity > 0:
      if v_test:
        print(f'Test expression: {v_test}\n')
        print(f'Evaluated result {OK}')
      if isinstance(result,Box):          # Remove stuff that will crash JSON serialization
        result.pop('re',None)
        if isinstance(result.result,Box):
          result.pop('result',None)
      print(f'Result received from {node.name}\n{"-" * 80}\n{result.to_json()}\n')

  if OK is not None and not OK:               # We have a real result (not skipped) that is not OK
    if report_error:
      report.p_test_fail(node.name,v_entry,topology)
      report.increase_fail_count(v_entry)
    return bool(OK)
  elif OK:                                    # ... or we might have a positive result
    if report_success:
      report.log_progress(f'Validation succeeded on {node.name}',topology)
      report.increase_pass_count(v_entry)

    return bool(OK)
  return OK
