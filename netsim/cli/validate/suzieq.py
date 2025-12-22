#
# SuzieQ functions for the netlab validate command
#
import typing

from box import Box, BoxList

from ... import data
from ...utils import log
from ..connect import LogLevel, connect_to_tool
from . import report, utils

'''
get_result: Execute a command on SuzieQ container, return parsed results
'''
def get_result(v_entry: Box, n_name: typing.Optional[str], topology: Box, verbosity: int) -> Box:
  if not 'suzieq' in topology.tools:
    log.fatal('SuzieQ tools is not used in this topology, cannot continue the validation process')

  v_cmd = v_entry.suzieq.show                               # Command to execute
  if n_name:
    v_cmd += f' --hostname {n_name}'
  v_cmd += ' --format json'
  err_value = data.get_box({'_error': True})                # Assume an error

  if verbosity >= 3:                                        # Extra-verbose: print command to execute
    print(f'Preparing to execute {v_cmd} on suzieq')

  # Set up arguments for the 'netlab connect' command and execute it
  #
  result = connect_to_tool('suzieq',v_cmd,topology,LogLevel.NONE,need_output=True)

  if verbosity >= 3:                                        # Extra-verbose: print the results we got
    print(f'Executed {v_cmd} got {result}')

  # If the result we got back is not a string, the 'netlab connect' command
  # failed in one way or another
  #
  if not isinstance(result,str):
    report.log_failure(
      f'Failed to execute suzieq command "{v_cmd}"',
      topology=topology)
    return err_value

  # Try to parse the results we got back as JSON data
  #
  j_result = utils.parse_JSON(result)
  if isinstance(j_result,Exception):
    report.log_failure(
      f'Failed to parse result output of suzieq command "{v_cmd}"',
      more_data = str(j_result),
      topology=topology)
    return err_value

  return j_result


'''
Execute validation of SuzieQ results. The only difference with the 'regular' validation is that
this one has to iterate over the list of records returned by SuzieQ
'''
def execute_validation(
      v_entry: Box,
      node: Box,
      topology: Box,
      result: typing.Union[Box,BoxList],
      verbosity: int,
      report_error: bool) -> typing.Optional[bool]:

  C_OK = None
  if isinstance(result,Box):
    C_OK = utils.execute_validation_expression(v_entry,node,topology,result,verbosity,report_error)
  else:
    for record in result:
      for kw in ['assert']:
        if kw in record:
          record[f'_{kw}'] = record[kw]
    
      R_OK = utils.execute_validation_expression(v_entry,node,topology,record,verbosity,report_error,report_success=False)
      if C_OK is None:
        C_OK = bool(R_OK)
      elif R_OK is not None:
        if v_entry.suzieq.get('valid','any') == 'any':
          C_OK = C_OK or bool(R_OK)
        else:
          C_OK = C_OK and bool(R_OK)

  if C_OK is None:
    return C_OK
  if not C_OK:
    if report_error:
      report.p_test_fail(node.name,v_entry,topology)
      report.increase_fail_count(v_entry)
    return C_OK

  report.log_progress(f'Validation succeeded on {node.name}',topology)
  report.increase_pass_count(v_entry)
  return True
