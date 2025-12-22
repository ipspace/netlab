#
# Plugin functions for the "netlab validate" command
#
import os
import typing

from box import Box

from ... import data
from ...data import global_vars
from ...utils import files as _files
from ...utils import log
from . import report

_validation_plugins: dict = {}
PLUGIN_ERROR: dict = {}

'''
load_plugin: try to load the validation plugin for the specified device
'''

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
  for v_entry in v_path:                                              # Iterate over the search path
    v_file = f'{v_entry}/{device}.py'                                 # ... trying to find the device-specific plugin
    if os.path.exists(v_file):                                        # Got it?
      return _files.load_python_module(f'validate_{device}',v_file)   # ... cool, try to load the Python module

  err_key = f'plugin_{device}'
  if err_key not in PLUGIN_ERROR:
    indent = (topology._v_len + 3) if topology else 10
    log.error(
      f'Cannot find validation plugin for device {device}',
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

Figure out whether the validation plugin for the device under test provides the
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

  err_key = f'action_{node.device}_{func_name}'

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
  from . import TEST_COUNT

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
      report.log_info(
        msg=str(wn),
        f_status='SKIPPED',
        topology=topology)
    TEST_COUNT.skip += 1
    return None
  except AttributeError as ex:
    if p_name in str(ex):
      return None
    raise PluginEvalError(str(ex))
  except Exception as ex:
    raise PluginEvalError(str(ex))

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

  try:
    OK = exec_plugin_function('valid',v_entry,node,result)
    if OK is not None and not OK:
      if report_error:
        report.p_test_fail(node.name,v_entry,topology)
  except Exception as ex:
    if report_error:
      report.p_test_fail(node.name,v_entry,topology,str(ex))
    OK = False

  if (not OK and verbosity) or verbosity >= 2:
    print(f'Input data: {result.to_json()}')
    print(f'Plugin expression: {v_entry.plugin}\n')
    print(f'Evaluated result {OK}')

  if OK is not None:
    if OK:
      msg = f'{node.name}: {OK}' if isinstance(OK,str) else f'Validation succeeded on {node.name}'
      report.log_progress(msg,topology)
      report.increase_pass_count(v_entry)
    elif report_error:
      report.increase_fail_count(v_entry)

  return OK if OK is None else bool(OK)
