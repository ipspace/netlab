#
# netlab validate command
#
# Perform lab validation tests
#
import typing
import os
import sys
import argparse
import re
import time
import math
import traceback

from box import Box

from . import load_snapshot,parser_add_debug,parser_add_verbose
from ..utils import log,templates,strings,status as _status, files as _files
from ..data import global_vars
from ..augment import devices
from .. import data
from .connect import connect_to_node,LogLevel

#
# CLI parser for 'netlab validate' command
#
def validate_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in transformed lab topology')
  parser_add_debug(parser)                                # Add debugging options
  parser_add_verbose(parser)                              # ... and verbosity flag
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    '--list',
    dest='list',
    action='store_true',
    help='List validation tests')
  parser.add_argument(
    '--node',
    dest='nodes', action='store',
    help='Execute validation tests only on selected node(s)')
  parser.add_argument(
    '--skip-wait',
    dest='nowait', action='store_true',
    help='Skip the waiting period')
  parser.add_argument(
    '-e','--error-only',
    dest='error_only', action='store_true',
    help='Display only validation errors (on stderr)')
  parser.add_argument(
    '--skip-missing',
    dest='skip_missing', action='store_true',
    help=argparse.SUPPRESS)
  parser.add_argument(
    '--dump',
    action='store',
    choices=['result'],
    nargs='+',
    default=[],
    help='Dump additional information during validation process')
  parser.add_argument(
    dest='tests', action='store',
    nargs='*',
    help='Validation test(s) to execute (default: all)')

  return parser.parse_args(args)

# I'm cheating. Declaring a global variable is easier than passing 'args' argument around
#
ERROR_ONLY: bool = False
TEST_HEADER: dict = {}

'''
list_tests: display validation tests defined for the current lab topology
'''
def list_tests(topology: Box) -> None:
  heading = [ 'Test','Description','Nodes','Devices' ]
  rows = [
    [ v_entry.name,
      v_entry.description or '',
      ",".join(v_entry.nodes),
      ",".join(v_entry.devices) ]
    for v_entry in topology.validate ]
  strings.print_table(heading,rows)

# The following routines print colored test status and offer
# various levels of abstraction, from "give me a colored text"
# to "tell the user the lab was a great success"

# Prints test status (colored text in fixed width)
#
def p_status(txt: str, color: str, topology: Box, stderr: bool = False) -> None:
  txt = f'[{txt}]{" " * 80}'[:topology._v_len+3]
  strings.print_colored_text(txt,color,stderr=stderr)

# Print test header
#
def p_test_header(v_entry: Box,topology: Box) -> None:
  global TEST_HEADER
  h_text = v_entry.get('description','Starting test') + \
           (f' [ node(s): {",".join(v_entry.nodes)} ]' if v_entry.nodes else '')

  if ERROR_ONLY:
    TEST_HEADER = { 'name': v_entry.name, 'text': h_text }
    return

  p_status(v_entry.name,"bright_cyan",topology)
  print(h_text)

# Print generic "test failed" message
#
def log_failure(
      msg: str,
      topology: Box,
      f_status: str = 'FAIL',
      more_data: typing.Optional[str] = None) -> None:

  global TEST_HEADER,ERROR_ONLY
  if TEST_HEADER:
    print(file=sys.stderr)
    p_status(TEST_HEADER['name'],'red',topology,stderr=True)
    print(TEST_HEADER['text'],file=sys.stderr)
    TEST_HEADER = {}

  o_file = sys.stderr if ERROR_ONLY else sys.stdout
  p_status(f_status,'bright_red',topology,stderr=ERROR_ONLY)
  print(msg,file=o_file)
  if more_data:
    p_status('MORE','bright_black',topology,stderr=ERROR_ONLY)
    print(more_data,file=o_file)

# Print generic "making progress" message
#
def log_progress(msg: str, topology: Box, f_status: str = 'PASS') -> None:
  global ERROR_ONLY
  if ERROR_ONLY:
    return

  p_status(f_status,'light_green',topology)
  print(msg)

# Print generic "ambivalent info" message
#
def log_info(msg: str, topology: Box, f_status: str = 'INFO') -> None:
  global ERROR_ONLY
  if ERROR_ONLY:
    return

  p_status(f_status,'yellow',topology)
  print(msg)

# Print "test failed on node"
#
def p_test_fail(n_name: str, v_entry: Box, topology: Box) -> None:
  err = v_entry.get('fail','')
  err = f'Node {n_name}: '+err if err else f'Test failed for node {n_name}'
  log_failure(err,topology)

# Print "test passed"
#
def p_test_pass(v_entry: Box, topology: Box) -> None:
  msg = v_entry.get('pass','Test succeeded')
  log_progress(msg,topology)

_validation_plugins: dict = {}

'''
extend_first_wait_time: some devices need extra time to start working, even when
the configuration process has completed. Assuming we can't (or don't want to)
catch that during the device readiness check, we should add extra delay to the
validation process.

This function walks through the lab nodes, checks the features.initial.delay of
each device, and adds the maximum delay to the first 'wait' parameter.
'''

def extend_first_wait_time(args: argparse.Namespace, topology: Box) -> None:
  max_delay = 0
  d_device  = None
  for n_data in topology.nodes.values():
    d_features = devices.get_device_features(n_data,topology.defaults)
    d_delay = d_features.get('initial.delay',None)
    if not d_delay:
      continue
    if d_delay > max_delay:                                           # Found a device that requires a delay
      max_delay = d_delay                                             # ... take the max value of the delay
      d_device  = n_data.device                                       # ... and remember the device causing it

  if not max_delay:                                                   # No slow devices in lab topology, exit
    return

  for v_entry in topology.validate:
    if not v_entry.get('wait',0):                                     # No wait associated with this entry, move on
      continue

    v_entry.wait = v_entry.wait + max_delay
    if not args.error_only:
      indent = (topology._v_len + 3) if topology else 10
      log.error(
        f'Initial wait time extended by {max_delay} seconds required by {d_device}',
        category=Warning,
        module='',indent=indent)
    return

'''
load_plugin: try to load the validation plugin for the specified device
'''

PLUGIN_ERROR: dict = {}

def load_plugin(device: str) -> typing.Any:
  global PLUGIN_ERROR
  topology = global_vars.get_topology()
  if topology is None:                                                # Abort if we can't get a point to the topology
    return None

  v_path = topology.defaults.paths.validate or ['topology:validate']  # Get validation plugin path
  v_base = os.path.dirname(topology.input[0])                         # Get base (topology) directory
  v_path = _files.absolute_search_path(v_path,v_base)                 # Get the absolute search path
  if log.VERBOSE >= 2:
    print(f'Searching for {device} plugin in {v_path}')
  for v_entry in v_path:                                              # Iterate over the seach path
    v_file = f'{v_entry}/{device}.py'                                 # ... trying to find the device-specific plugin
    if os.path.exists(v_file):                                        # Got it?
      return _files.load_python_module(f'validate_{device}',v_file)   # ... cool, try to load the Python module

  err_key = f'plugin_{device}'
  if err_key not in PLUGIN_ERROR:
    indent = (topology._v_len + 3) if topology else 10
    log.error(
      'Cannot find validation plugin for device {device}',
      category=log.MissingDependency,
      module='validate',
      indent=indent)
    PLUGIN_ERROR[err_key] = True

  return None

'''
find_plugin -- find the validation plugin

The plugin could have been already loaded, in which case we'll find it in the global
_validation_plugin dictionary, or we have to load it, in which case we'll save it in
the same dictionary for the next lookup.

Please note that even the negative results ('there is no such plugin') are cached.
'''
def find_plugin(device: str) -> typing.Any:
  global _validation_plugins
  if device in _validation_plugins:
    return _validation_plugins[device]

  plugin = load_plugin(device)
  _validation_plugins[device] = plugin
  return plugin

'''
find_plugin_action -- find the action (show/exec) from the plugin

Figure out whether the validation plugin for the device under test providers the
desired functionality (show_ or exec_ function). If not, the test is skipped.
'''
def find_plugin_action(v_entry: Box, node: Box) -> typing.Optional[str]:
  global PLUGIN_ERROR

  if 'plugin' not in v_entry:
    return None

  plugin = find_plugin(node.device)
  if not plugin:
    return None

  func_name = v_entry.plugin.split('(')[0]
  for kw in ('show','exec'):
    if getattr(plugin,f'{kw}_{func_name}',None):
      return kw

  err_key = 'action_{node.device}_{func_name}'

  if err_key not in PLUGIN_ERROR:
    topology = global_vars.get_topology()
    indent = (topology._v_len + 3) if topology else 10
    log.error(
      f"Validation plugin for device {node.device} has no action for test '{func_name}'",
      category=log.MissingDependency,
      module='validate',
      indent=indent)
  return None

class PluginEvalError(Exception):     # Exception class used to raise plugin evaluation exceptions
  pass

'''
Execute the plugin function specified by 'action' variable and 'plugin' v_entry value

The magic part of this function is the preparation step:

* We pretend the device-specific validation plugin is imported into the current context
  as 'validate_XXX' module
* We pass a copy of the topology data as locals to the validation function (ensuring all
  changes made to topology data are discarded)
* The topology data is augmented with 'node' variable (current node data)
* The results of the 'exec' or 'show' command (if available) are passed as _result global
  to the validation plugin

Finally, the validation expression is executed and the exceptions are handled:

* AttributeError exception including 'validate_XXX' in the error text indicates the
  function we tried to call does not exist, in which case we return None (test skipped)
* Any other error is re-raised as PluginEvalError exception to signal to the caller
  that the plugin evaluatino function failed.

Please note that custom exception raised in the plugin functions get re-raised as
PluginEvalError exceptions, resulting in custom error messages.
'''
def exec_plugin_function(action: str, v_entry: Box, node: Box, result: typing.Optional[Box] = None) -> typing.Any:
  global test_skip_count

  p_name = f'validate_{node.device}'
  exec = f'{p_name}.{action}_{v_entry.plugin}'
  exec_data = data.get_box(global_vars.get_topology() or {}) + v_entry.vars
  exec_data.node = node

  plugin = find_plugin(node.device)               # Find device-specific validation plugin
  if plugin is None:                              # Not found, the test is skipped
    return None
  plugin._result = result
  global_vars.set_result_dict('_result',result or Box({}))
  exec_data[p_name] = plugin

  try:
    return eval(exec,{},exec_data)
  except log.Result as wn:
    return str(wn)
  except log.Skipped as wn:                       # The requested test is not implemented in the validation function
    topology = global_vars.get_topology()
    if topology is not None:
      log_info(
        msg=str(wn),
        f_status='SKIPPED',
        topology=topology)
    test_skip_count += 1
    return None
  except AttributeError as ex:
    if p_name in str(ex):
      return None
    raise PluginEvalError(str(ex))
  except Exception as ex:
    raise PluginEvalError(str(ex))

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
      value = exec_plugin_function(action,v_entry,node)
    except PluginEvalError as ex:
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

'''
Execute a 'show' command. The return value is expected to be parseable JSON
'''
def get_parsed_result(v_entry: Box, n_name: str, topology: Box, verbosity: int) -> Box:
  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = get_exec_list(v_entry,'show',node,topology)       # ... and the 'show' action for the current node
  err_value = data.get_box({'_error': True})                # Assume an error

  if not v_cmd:                                             # We should not get here, but we could...
    indent = (topology._v_len + 3) if topology else 10
    log.error(
      f'Test {v_entry.name}: have no idea what show command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation',
      indent=indent)
    return err_value

  if verbosity >= 3:                                        # Extra-verbose: print command to execute
    print(f'Preparing to execute {v_cmd}')

  # Set up arguments for the 'netlab connect' command and execute it
  #
  args = argparse.Namespace(quiet=True,host=n_name,output=True,show=v_cmd,verbose=False)
  result = connect_to_node(args=args,rest=[],topology=topology,log_level=LogLevel.NONE)

  if verbosity >= 3:                                        # Extra-verbose: print the results we got
    print(f'Executed {v_cmd} got {result}')

  # If the result we got back is not a string, the 'netlab connect' command
  # failed in one way or another
  #
  if not isinstance(result,str):
    log_failure(
      f'Failed to execute show command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',
      topology=topology)
    return err_value

  # Try to parse the results we got back as JSON data
  #
  j_result = parse_JSON(result)
  if isinstance(j_result,Exception):
    log_failure(
      f'Failed to parse result output of "{" ".join(v_cmd)}" on {n_name} (device {node.device}) as JSON',
      more_data = str(j_result),
      topology=topology)
    return err_value

  return j_result

'''
Execute a command on the device and return stdout
'''
def get_result_string(
      v_entry: Box,
      n_name: str,
      topology: Box,
      report_error: bool = True) -> typing.Union[bool,str]:

  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = get_exec_list(v_entry,'exec',node,topology)       # ... and the 'exec' action for the current node
  if not v_cmd:                                             # We should not get here, but we could...
    indent = (topology._v_len + 3) if topology else 10
    log.error(
      f'Test {v_entry.name}: have no idea what command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation',
      indent=indent)
    return False

  # Set up arguments for the 'netlab connect' command and execute it
  #
  args = argparse.Namespace(quiet=True,host=n_name,output=True,show=None,verbose=False)
  result = connect_to_node(args=args,rest=v_cmd,topology=topology,log_level=LogLevel.NONE)

  if result is False:                                       # Report an error if 'netlab connect' failed
    if report_error:
      log_failure(
        f'Failed to execute command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',topology)

  return result

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
  for kw in ('show','exec'):
    if kw not in v_entry:
      continue
    if isinstance(v_entry[kw],(str,int)):
      return kw
    if node.device in v_entry[kw]:
      return kw

  if 'plugin' in v_entry:
    return find_plugin_action(v_entry,node)

  if 'wait' in v_entry:
    return 'wait'

  return None

'''
wait_before_testing -- wait for specified time since lab start time or previous test
'''
def wait_before_testing(
      v_entry: Box,
      start_time: typing.Optional[typing.Union[int,float]],
      topology: Box) -> None:
  if not 'wait' in v_entry:
    return

  if start_time is None:
    wait_time = v_entry.wait
  else:
    wait_time = math.ceil(start_time + v_entry.wait - time.time())

  if wait_time > 0 and 'wait_msg' in v_entry:         # Print the initial "we're waiting for this" message
    log_info(
      v_entry.wait_msg,
      f_status = 'WAITING',
      topology=topology)

  while wait_time >= 0:
    log_info(                                         # Have to wait some more, print a logging message
      f'Waiting for {v_entry.wait} seconds, {wait_time} seconds left',
      f_status = 'WAITING',
      topology=topology)

    time.sleep(wait_time if wait_time < 5 else 5)     # Wait no more than five seconds
    wait_time = wait_time - 5

test_skip_count: int
test_result_count: int
test_pass_count: int

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
      result: Box,
      verbosity: int,
      report_error: bool) -> typing.Optional[bool]:

  global test_skip_count,test_result_count,test_pass_count
  global BUILTINS

  v_test = get_entry_value(v_entry,'valid',node,topology)
  if not v_test:                              # Do we have a validation expression for the current device?
    log_info(                                 # ... nope, have to skip it
      f'Test results validation not defined for device {node.device} / node {node.name}',
      f_status = 'SKIPPED',
      topology=topology)
    test_skip_count += 1
    return None
  else:
    try:                                      # Otherwise try to evaluate the validation expression
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
      for kw in ('re','result'):              # Remove stuff that will crash JSON serialization
        result.pop(kw,None)
      print(f'Result received from {node.name}\n{"-" * 80}\n{result.to_json()}\n')

  if OK is not None and not OK:               # We have a real result (not skipped) that is not OK
    if report_error:
      p_test_fail(node.name,v_entry,topology)
      test_result_count += 1
    return bool(OK)
  elif OK:                                    # ... or we might have a positive result
    log_progress(f'Validation succeeded on {node.name}',topology)
    test_result_count += 1
    test_pass_count += 1
    return bool(OK)

  return OK

"""
execute_validation_plugin:

* Execute the valid_xxx function in the validation plugin
* Process the results similarly to the execute_validation_expression function

Exception handling:

* If the 'exec_plugin_function' throws an exception, log the failure and assume the test has failed
"""
def execute_validation_plugin(
      v_entry: Box,
      node: Box,
      topology: Box,
      result: Box,
      verbosity: int,
      report_error: bool) -> typing.Optional[bool]:

  global test_skip_count,test_result_count,test_pass_count

  try:
    OK = exec_plugin_function('valid',v_entry,node,result)
    if OK is not None and not OK:
      if report_error:
        p_test_fail(node.name,v_entry,topology)
  except Exception as ex:
    if report_error:
      log_failure(f'{node.name}: {str(ex)}',topology)
    OK = False

  if (not OK and verbosity) or verbosity >= 2:
    print(f'Input data: {result.to_json()}')
    print(f'Plugin expression: {v_entry.plugin}\n')
    print(f'Evaluated result {OK}')

  if OK is not None:
    if report_error or OK:
      test_result_count += 1
    if OK:
      msg = f'{node.name}: {OK}' if isinstance(OK,str) else f'Validation succeeded on {node.name}'
      log_progress(msg,topology)
      test_pass_count += 1

  return OK if OK is None else bool(OK)

'''
Execute node validation
'''
def execute_node_validation(
      v_entry: Box,
      topology: Box,
      n_name: str,
      report_error: bool,
      args: argparse.Namespace) -> typing.Tuple[typing.Optional[bool],typing.Optional[bool]]:

  global test_skip_count,test_result_count,test_pass_count

  node = topology.nodes[n_name]
  result = data.get_empty_box()

  action = find_test_action(v_entry,node)       # Find the action to show/execute/wait
  if action == 'wait':                          # Test with pure 'wait'
    return (True,True)                          # is assumed to be successful

  if action is None:                            # None found, skip this node
    log_info(
      f'Test action not defined for device {node.device} / node {n_name}',
      f_status='SKIPPED',
      topology=topology)
    test_skip_count += 1                        # Increment skip count for test results summary
    return (True,None)                          # Processed, unknown result

  if args.verbose >= 2:                         # Print out what will be executed
    cmd = get_entry_value(v_entry,action,node,topology)
    print(f'{action} on {node.name}/{node.device}: {cmd}')

  if action == 'show':                          # We got a 'show' action, try to get parsed results
    result = get_parsed_result(v_entry,n_name,topology,args.verbose)
    if '_error' in result:                      # OOPS, we failed (unrecoverable)
      test_result_count += 1                    # Increase result count
      return (True, False)                      # ... and return (processed, failed)
  elif action == 'exec':                        # We got an 'exec' action, try to get something out of the device
    result.stdout = get_result_string(v_entry,n_name,topology,report_error)
    if result.stdout is False:                  # Did the exec command fail?
      if report_error:
        test_result_count += 1
        return (True, False)                    # Return (processed, failed)

  OK = None
  if 'valid' in v_entry:                        # Do we have a validation expression in the test entry?
    OK = execute_validation_expression(v_entry,node,topology,result,args.verbose,report_error)
  elif 'plugin' in v_entry:                     # If not, try to call the plugin function
    OK = execute_validation_plugin(v_entry,node,topology,result,args.verbose,report_error)
  elif 'pass' in v_entry:
    log_progress(f"{node.name}: {v_entry['pass']}",topology)

  if OK is False:                               # Validation failed...
    if not report_error:                        # ... but we still don't have to report it?
      return (False, None)                      # ... return (not processed, unknown)
    if 'result' in args.dump:                   # Do we have to dump the result for further troubleshooting?
      if isinstance(result,Box):                # If the result is a Box, clean it first
        for kw in ['re']:                       # ... remove extra keys first
          result.pop(kw,None)
        # ... and remove the 'result' key if it's not needed
        if 'result' in result and isinstance(result.result,Box):
          result.pop('result',None)
      print(f'Returned result\n{"=" * 80}\n{result.to_yaml()}')

  return (True, OK)                             # ... otherwise return (processed, validation result)

'''
Execute a single validation test on all specified nodes
'''
def execute_validation_test(
      v_entry: Box,
      topology: Box,
      start_time: typing.Optional[typing.Union[int,float]],
      args: argparse.Namespace) -> typing.Optional[bool]:
  global test_skip_count,test_result_count,test_pass_count

  # Return value uses ternary logic: OK (True), Fail(False), Skipped (None)
  ret_value = None

  p_test_header(v_entry,topology)                 # Print test header
  if 'wait' in v_entry and not v_entry.nodes:     # Handle pure wait case
    if not args.nowait:
      wait_before_testing(v_entry,start_time,topology)
    return None

  if not v_entry.nodes:
    log_info(
      f'There are no nodes specified for this test, skipping...',
      f_status='SKIPPED',
      topology=topology)
    test_skip_count += 1
    return None

  wait_time = 0 if args.nowait else v_entry.get('wait',0)
  start_time= time.time()
  stop_time = start_time + wait_time              # Time to wait for successful result
  wait_msg  = v_entry.get('wait_msg',None)        # Message to display if starting sleep after the first try
  wait_time = time.time()                         # Time to display first 'waiting' message
  wait_cnt  = 0                                   # How many 'waiting' messages did we display?
  n_remaining: list = v_entry.nodes               # Start with all nodes specified in the validation entry

  while n_remaining:                              # Keep retrying 
    for n_name in n_remaining:                    # Iterate over remaining nodes
      (proc,OK) = execute_node_validation(v_entry,topology,n_name,time.time() >= stop_time,args)
      if proc:                                    # Have we processed this node? Remove node from remaining list
        n_remaining = [ x for x in n_remaining if x != n_name ]

      # The result could be 'True', 'False', or 'None' (don't know)
      if OK is True and ret_value is None:        # If we have a True result and we don't know the composite result yet
        ret_value = True                          # ... set composite result to True
      elif OK is False:                           # But if we have a single failure ...
        ret_value = False                         # ... set composite result to False (failure)

    if ret_value is not False and n_remaining and wait_msg:
      if wait_time < time.time():
        if 'wait' in v_entry and wait_cnt == 0:
          extra_msg = f' (retrying for {v_entry.wait} seconds)'
        else:
          extra_msg = f' ({int(stop_time - time.time())} seconds left)'
        log_info(
          wait_msg + extra_msg,
          f_status = 'WAITING',
          topology=topology)
        wait_cnt += 1                             # Next message will be X seconds left
        wait_time += 15                           # ... and it will happen after 15 seconds
      time.sleep(1)

  if ret_value:                                   # If we got to 'True'
    if wait_cnt:
      log_info(
        f'Succeeded in { round(time.time() - start_time,1) } seconds',
        f_status = 'PASS',
        topology=topology)
    p_test_pass(v_entry,topology)                 # ... declare Mission Accomplished

  return ret_value

'''
filter_by_test: select only tests specified in arguments
'''
def filter_by_tests(args: argparse.Namespace, topology: Box) -> None:
  if not args.tests:
    return

  for t in args.tests:
    find_test = [ v_entry for v_entry in topology.validate if v_entry.name == t ]
    if not find_test:
      log.error(
        f'Invalid test name {t}, use "netlab validate --list" to list test names',
        category=log.IncorrectValue,
        module='validation')

  if log.pending_errors():
    return

  topology.validate = [ v_entry for v_entry in topology.validate if v_entry.name in args.tests ]

'''
filter_by_nodes: select only tests executed on specified node
'''
def filter_by_nodes(args: argparse.Namespace, topology: Box) -> None:
  if not args.nodes:
    return

  node_list = args.nodes.split(',')
  node_set  = set(node_list)

  for n in node_list:
    if not n in topology.nodes:
      log.error(
        f'Invalid node name {n}, use "netlab inspect nodes" to list nodes in your lab',
        category=log.IncorrectValue,
        module='validation')

  if log.pending_errors():
    return

  topology.validate = [ v_entry for v_entry in topology.validate if set(v_entry.nodes) & node_set ]
  if not topology.validate:
    log.error(
      f'No tests are executed on any of the specified nodes',
      category=log.IncorrectValue,
      module='validation')
    return

  for v_entry in topology.validate:
    v_entry.nodes = [ n for n in v_entry.nodes if n in node_list ]

'''
Main routine: run all tests, handle validation errors, print summary results
'''
def run(cli_args: typing.List[str]) -> None:
  global test_skip_count,test_result_count,test_pass_count,ERROR_ONLY
  args = validate_parse(cli_args)
  log.set_logging_flags(args)
  topology = load_snapshot(args)

  if 'validate' not in topology:
    if args.skip_missing:
      sys.exit(2)
    else:
      log.fatal('No validation tests defined for the current lab, exiting')

  if args.list:
    list_tests(topology)
    return

  filter_by_tests(args,topology)
  filter_by_nodes(args,topology)
  log.exit_on_error()

  templates.load_ansible_filters()

  ERROR_ONLY = args.error_only
  status = True
  cnt = 0
  test_skip_count = 0
  test_result_count = 0
  test_pass_count = 0
  topology._v_len = max([ len(v_entry.name) for v_entry in topology.validate ] + [ 7 ])
  start_time = _status.lock_timestamp() or time.time()
  log.init_log_system(header=False)
  extend_first_wait_time(args,topology)

  for v_entry in topology.validate:
    if cnt and not ERROR_ONLY:
      print()

    try:
      result = execute_validation_test(v_entry,topology,start_time,args)
    except KeyboardInterrupt:
      print("")
      log.fatal('Validation test interrupted')
    except:
      traceback.print_exc()
      log.fatal('Unhandled exception')

    if result is False:
      status = False
      if v_entry.stop_on_error:
        print()
        log_failure('Mandatory test failed, validation stopped',topology)
        sys.exit(1)

    if 'wait' in v_entry:
      start_time = time.time()

    cnt = cnt + 1

  if not ERROR_ONLY:
    print()
    if test_pass_count and test_pass_count == test_result_count:
      log_progress(f'Tests passed: {test_pass_count}',topology,f_status='SUCCESS')
    elif test_result_count:
      log_failure('Tests completed, validation failed',topology)

    if test_skip_count:
      log_info('Some tests were skipped, the results are not reliable',topology)

  sys.exit(0 if status else 1)
