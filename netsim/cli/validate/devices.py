#
# Device-handling functions for the "netlab validate"
#
# Execute a command or deploy a custom config on the specified node
#
import argparse
import typing

from box import Box

from ... import data
from ...utils import log
from .. import external_commands
from ..connect import LogLevel, connect_to_node
from . import report, utils

'''
Execute a 'show' command. The return value is expected to be parseable JSON
'''
def get_parsed_result(v_entry: Box, n_name: str, topology: Box, verbosity: int) -> Box:
  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = utils.get_exec_list(v_entry,'show',node,topology) # ... and the 'show' action for the current node
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
  args = argparse.Namespace(quiet=True,output=True,show=v_cmd,verbose=False)
  result = connect_to_node(node=n_name,args=args,rest=[],topology=topology,log_level=LogLevel.NONE)

  if verbosity >= 3:                                        # Extra-verbose: print the results we got
    print(f'Executed {v_cmd} got {result}')

  # If the result we got back is not a string, the 'netlab connect' command
  # failed in one way or another
  #
  if not isinstance(result,str):
    report.log_failure(
      f'Failed to execute show command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',
      topology=topology)
    return err_value

  # Try to parse the results we got back as JSON data
  #
  j_result = utils.parse_JSON(result)
  if isinstance(j_result,Exception):
    report.log_failure(
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
      report_error: bool = True) -> typing.Union[bool,int,str]:

  node = topology.nodes[n_name]                             # Get the node data
  v_cmd = utils.get_exec_list(v_entry,'exec',node,topology) # ... and the 'exec' action for the current node
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
  args = argparse.Namespace(quiet=True,output=True,show=None,verbose=False)
  result = connect_to_node(node=n_name,args=args,rest=v_cmd,topology=topology,log_level=LogLevel.NONE)

  if result is False:                                       # Report an error if 'netlab connect' failed
    if report_error:
      report.log_failure(
        f'Failed to execute command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',topology)

  return result

'''
Execute device configuration requests via 'netlab config'

The validation entry has:

* 'config' attribute that is passed to 'netlab config'
* 'nodes' list that is used to build the '--limit' argument 
'''
def execute_netlab_config(v_entry: Box, topology: Box) -> bool:
  node_str = ",".join(v_entry.nodes)
  cmd = f'netlab config {v_entry.config.template} --limit {node_str}'.split(' ')
  v_dump = []
  for k,v in v_entry.config.variable.items():
    cmd += [ '-e', k + '="' + str(v).replace('"','\\"') + '"' ]
    v_dump += [ f'{k}={v}' ]
  if log.VERBOSE:
    print(f'Executing {cmd}')
  v_dump_str = " with " + " ".join(v_dump) if v_dump else ""
  report.log_info(f'Executing configuration snippet {v_entry.config.template}{v_dump_str}',topology)
  if external_commands.run_command(cmd,check_result=True,ignore_errors=True,return_stdout=True):
    report.increase_pass_count(v_entry)
    msg = v_entry.get('pass','Devices configured')
    report.log_progress(msg,topology)
    return True
  
  report.log_failure(
    f'"{cmd}" failed',
    topology,
    more_data='Execute the command manually to figure out what went wrong')
  report.increase_fail_count(v_entry)
  return False
