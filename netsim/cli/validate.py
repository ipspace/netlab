#
# netlab inspect command
#
# Inspect data structures in transformed lab topology
#
import typing
import os
import sys
import argparse

from box import Box
from termcolor import colored

from . import load_snapshot
from ..utils import strings,log,templates
from .. import data
from .connect import connect_to_node,LogLevel

#
# CLI parser for 'netlab inspect' command
#
def inspect_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in transformed lab topology')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    '--node',
    dest='node', action='store',
    help='Execute validation tests only on selected node')
  parser.add_argument(
    dest='tests', action='store',
    nargs='?',
    help='Validation test(s) to execute (defaul: all)')

  return parser.parse_args(args)

'''
calculate_device_support: Figure out which devices are supported by the current validation test

If the validation entry includes 'devices' we're good to go -- hopefully the topology creator
knows what he's doing. Otherwise, we'll take a union of devices mentioned in 'show' and 'exec'
entries and do an intersectiion with the 'valid' entry
'''

def calculate_device_support(t_name: str, v_entry: Box, topology: Box) -> bool:
  if 'devices' in v_entry:
    return True
  
  d_set: typing.Set = set()
  for kw in ('show','exec'):
    if kw not in v_entry:
      continue
    if isinstance(v_entry[kw],str):
      continue
    d_set = d_set | set(v_entry[kw].keys())

  if 'valid' in v_entry:
    if isinstance(v_entry.valid,dict):
      d_set = d_set & set(v_entry.valid.keys())

  v_entry.devices = sorted(list(d_set))
  if not v_entry.devices:
    log.error(
      f'Validation test {t_name} is not supported by any valid device',
      category=log.MissingValue,
      module='validation')
    return False
  
  return True

'''
check_device_support:

  Given a validation test, list of nodes, and list of supported devices, figure out if
  it makes sense to execute the test.
'''
def check_device_support(t_name: str,v_entry: Box,topology: Box) -> bool:
  if not v_entry.nodes:
    log.error(
      f'Validation test "{t_name}" does not have a list of nodes it should be executed on',
      category=log.MissingValue,
      module='validation')
    return False
  
  result = True
  for n in v_entry.nodes:
    n_device = topology.nodes[n].device
    if not n_device in v_entry.devices:
      log.error(
        f'Cannot execute validation test "{t_name}" on node {n} (device {n_device})\n'+ \
        f'... This test can only be executed on {", ".join(v_entry.devices)}',
        category=log.IncorrectValue,
        module='validation')
      result = False

  return result

# Prepare test status (colored text in fixed width)
#
def p_status(txt: str, color: str, topology: Box) -> str:
  txt = f'[{txt}]{" " * 80}'[:topology._v_len+3]
  return colored(txt,color)

# Print test header
#
def p_test_header(t_name: str, v_entry: Box,topology: Box) -> None:
  print(
    p_status(t_name,"light_blue",topology) + \
    v_entry.get('description','Starting test') + \
    f' [ node(s): {",".join(v_entry.nodes)} ]')

# Print generic "test failed" message
#
def log_failure(msg: str, topology: Box, f_status: str = 'FAIL') -> None:
  print(p_status(f_status,'light_red',topology) + msg)

# Print generic "making progress" message
#
def log_progress(msg: str, topology: Box, f_status: str = 'PASS') -> None:
  print(p_status(f_status,'light_green',topology) + msg)

# Print "test failed on node"
#
def p_test_fail(t_name: str, n_name: str, v_entry: Box, topology: Box) -> None:
  err = v_entry.get('fail','')
  err = f'Node {n_name}: '+err if err else f'Test failed for node {n_name}'
  log_failure(err,topology)

# Print "test passed"
#
def p_test_pass(t_name: str, n_name: str, v_entry: Box, topology: Box) -> None:
  msg = v_entry.get('pass','Test succeeded')
  log_progress(msg,topology)

# Print "all tests succeeded"
#
def p_success(topology: Box) -> None:
  print()
  log_progress('All tests passed',topology,f_status='SUCCESS')

'''
Get generic or per-device action from a validation entry
'''
def get_entry_value(v_entry: Box, action: str, node: Box) -> typing.Any:
  n_device = node.device
  value = v_entry[action][n_device] if isinstance(v_entry[action],dict) else v_entry[action]
  if not isinstance(value,str):
    return value
  
  if '{{' in value:
    value = templates.render_template(data=node,j2_text=value)
#    print(f"{action} value for {node.name}: {value}")

  return value  

'''
Get the command to execute on the device in list format
'''
def get_exec_list(t_name: str, v_entry: Box, action: str, node: Box) -> list:
  v_cmd = get_entry_value(v_entry,action,node)
  if isinstance(v_cmd,list):
    return v_cmd
  elif isinstance(v_cmd,str):
    return v_cmd.split(' ')

  return []

'''
Execute a 'show' command. The return value is expected to be parseable JSON
'''
def get_parsed_result(t_name: str, v_entry: Box, n_name: str, topology: Box) -> Box:
  node = topology.nodes[n_name]
  v_cmd = get_exec_list(t_name,v_entry,'show',node)
  err_value = data.get_box({'_error': True})
  if not v_cmd:
    log.error(
      f'Test {t_name}: have no idea what show command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation')
    return err_value

  args = argparse.Namespace(quiet=True,host=n_name,output=True,show=v_cmd)
  result = connect_to_node(args=args,rest=[],topology=topology,log_level=LogLevel.NONE)

  if not isinstance(result,str):
    log_failure(
      f'Failed to execute show command "{" ".join(v_cmd)}" on {n_name} (device {node.device})',
      topology=topology)
    return err_value

  try:
    return Box.from_json(result)
  except:
    log_failure(
      f'Failed to parse result output of "{" ".join(v_cmd)}" on {n_name} (device {node.device}) as JSON',
      topology=topology)
    return err_value

'''
Execute a command on the device and return stdout
'''
def get_result_string(t_name: str, v_entry: Box, n_name: str, topology: Box) -> typing.Union[bool,str]:
  node = topology.nodes[n_name]
  v_cmd = get_exec_list(t_name,v_entry,'exec',node)
  if not v_cmd:
    log.error(
      f'Test {t_name}: have no idea what command to execute on node {n_name} / device {node.device}',
      category=log.MissingValue,
      module='validation')
    return False

  args = argparse.Namespace(quiet=True,host=n_name,output=True)
  result = connect_to_node(args=args,rest=v_cmd,topology=topology,log_level=LogLevel.NONE)
  if result is False:
    log.error('Failed to execute command {v_cmd} on {n_name} (device {n_device})')

  return result

'''
Execute a single validation test on all specified nodes
'''
def execute_validation_test(t_name: str,v_entry: Box,topology: Box) -> bool:
  ret_value = True

  p_test_header(t_name,v_entry,topology)
  for n_name in v_entry.nodes:
    node = topology.nodes[n_name]
    result = data.get_empty_box()
    if v_entry.show:
      result = get_parsed_result(t_name,v_entry,n_name,topology)
      if '_error' in result:
        ret_value = False
        continue
    elif v_entry.exec:
      result.stdout = get_result_string(t_name,v_entry,n_name,topology)
      if result.stdout is False:
        ret_value = False
        continue

    if 'valid' in v_entry:
      v_test = get_entry_value(v_entry,'valid',node)
      try:
        OK = eval(v_test,{'__builtins': {}},result)
      except:
        OK = False

      if not OK:
        p_test_fail(t_name,n_name,v_entry,topology)
        ret_value = False
      else:
        log_progress(f'Validation succeeded on {n_name}',topology)

  if ret_value:
    p_test_pass(t_name,n_name,v_entry,topology)

  return ret_value

def run(cli_args: typing.List[str]) -> None:
  args = inspect_parse(cli_args)
  topology = load_snapshot(args)

  if 'validate' not in topology:
    log.fatal('No validation tests defined for the current lab, exiting')

  for t_name,v_entry in topology.validate.items():
    if not calculate_device_support(t_name,v_entry,topology):
      continue

    check_device_support(t_name,v_entry,topology)

  log.exit_on_error()

  status = True
  cnt = 0
  topology._v_len = max([ len(t_name) for t_name in topology.validate.keys() ] + [ 7 ])

  for t_name,v_entry in topology.validate.items():
    if cnt:
      print()

    status = status and execute_validation_test(t_name,v_entry,topology)
    cnt = cnt + 1

  if status:
    p_success(topology)

  sys.exit(0 if status else 1)
