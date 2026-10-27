#
# Reporting functions for the "netlab validate" command
#
import sys
import time
import typing

from box import Box

from ... import __version__
from ...data import global_vars
from ...utils import log, strings

JSON_VERSION = 1
JSON_STATUS = {                               # Map logging status into JSON results
  'PASS': 'pass', 'SUCCESS': 'pass', 'FAIL': 'fail', 'WARNING': 'warning', 'SKIPPED': 'skip', 'ERROR': 'error' }
JSON_RANK = [ 'pass', 'skip', 'warning', 'fail', 'error' ]

'''
start_test, set_node, record_result: collect the results for the JSON printout

The results are recorded in the logging functions based on the current test/node
context and the status of the logged message. The last message wins, and execution
errors cannot be overwritten.
'''
def start_test(v_entry: Box) -> None:
  import netsim.cli.validate as _validate
  _validate.RESULTS['results'][v_entry.name] = {
    'description': v_entry.get('description',None),
    'level': v_entry.get('level',None),
    'result': None,
    'message': None,
    'elapsed': 0.0,
    'nodes': {},
    '_expect_fail': v_entry.get('_expect_fail',False) }
  _validate.CURRENT.clear()
  _validate.CURRENT.update({ 'test': v_entry.name, 'node': None, 'start': time.time() })

def set_node(n_name: typing.Optional[str]) -> None:
  import netsim.cli.validate as _validate
  if _validate.CURRENT:
    _validate.CURRENT['node'] = n_name

def record_result(f_status: str, msg: typing.Optional[str] = None) -> None:
  '''
  Log result into JSON data structure, optionally adding an error message
  '''
  import netsim.cli.validate as _validate
  ctx = _validate.CURRENT
  result = JSON_STATUS.get(f_status,None)         # Map uppercase log text into JSON result
  if result is None or not ctx.get('test'):
    return

  # Fetch the test results from the current test
  t_result = _validate.RESULTS['results'][ctx['test']]
  elapsed = round(time.time() - ctx['start'],1)
  t_result['elapsed'] = elapsed                   # Log maximum test-wide elapsed time
  n_name = ctx['node']                            # Is the result within the context of a node?
  if n_name:                                      # Node result, remove node name from the message
    topology = global_vars.get_topology()         # Fetch the device type (while dealing with imaginary edge cases)
    n_device = topology.nodes[n_name].device if topology is not None else None
    entry = t_result['nodes'].setdefault(n_name,{ 'device': n_device, 'result': None, 'message': None })
    if msg:
      msg = msg.removeprefix(f'Node {n_name}: ').removeprefix(f'{n_name}: ')
  else:                                           # Test-level result
    entry = t_result

  if entry['result'] != 'error':                  # Do not overwrite previous error result
    entry['result'] = result
  if msg is not None:                             # But always store message (when avaialble)
    entry['message'] = msg
  entry['elapsed'] = elapsed                      # ... and the elapsed time (which makes it max elapsed time)

def json_results(exit_code: int) -> dict:
  '''
  Build the JSON results document
  '''
  import netsim.cli.validate as _validate
  TC = _validate.TEST_COUNT
  summary = {
    'count': TC.count, 'passed': TC.passed, 'failed': TC.failed,
    'warning': TC.warning, 'skipped': TC.skip, 'error': 0 }
  results = {}
  for t_name,t_result in _validate.RESULTS['results'].items():
    expect_fail = t_result.pop('_expect_fail',False)
    entries = list(t_result['nodes'].values()) or [ t_result ]
    for entry in entries:                     # Errors are counted as failures (or warnings), move them
      if entry['result'] == 'error':
        summary['error'] += 1
        summary['warning' if t_result['level'] == 'warning' else 'failed'] -= 1
    if not expect_fail:                       # Test result is the worst node result (unless we expect a failure)
      for entry in t_result['nodes'].values():
        if entry['result'] and (not t_result['result'] or
            JSON_RANK.index(entry['result']) > JSON_RANK.index(t_result['result'])):
          t_result['result'] = entry['result']
    if t_result['result'] is None:            # Pure 'wait' entries don't produce results
      continue
    results[t_name] = t_result

  completed = _validate.RESULTS.get('completed',False)
  doc: dict = {
    'version': JSON_VERSION, 'netlab_version': __version__,
    'started': _validate.RESULTS.get('started',None),
    'exit_code': exit_code, 'aborted': not completed }
  if not completed:
    reason = _validate.RESULTS.get('reason',None)
    if not reason:                            # No explicit abort reason, use the last fatal/error message
      err_log = [                             # ... skipping hints and the generic 'exit on error' message
        line for line in log.get_error_log()
          if not line.startswith('...') and 'Cannot proceed beyond this point' not in line ]
      reason = err_log[-1] if err_log else 'Validation stopped'
    doc['reason'] = reason
  doc['summary'] = summary
  doc['results'] = results
  return doc

'''
increase_fail_count, increase_pass_count: Increase the counters based on test severity level
'''
def increase_fail_count(v_entry: Box, error: bool = False) -> None:
  from . import TEST_COUNT
  if error:                                   # Execution error (not a failed check)
    record_result('ERROR')
  TEST_COUNT.count += 1
  if v_entry.get('level',None) == 'warning':
    TEST_COUNT.warning += 1
  else:
    TEST_COUNT.failed += 1

def increase_pass_count(v_entry: Box) -> None:
  from . import TEST_COUNT
  TEST_COUNT.count += 1
  TEST_COUNT.passed += 1

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
  import netsim.cli.validate as _validate
  start_test(v_entry)
  h_text = v_entry.get('description','Starting test') + \
           (f' [ node(s): {",".join(v_entry.nodes)} ]' if v_entry.nodes else '')

  if _validate.ERROR_ONLY:
    _validate.TEST_HEADER = { 'name': v_entry.name, 'text': h_text }
    return

  p_status(v_entry.name,"bright_cyan",topology)
  print(h_text)

# Print generic "test failed" message
#
def log_failure(
      msg: str,
      topology: Box,
      f_status: str = 'FAIL',
      f_color: str = 'bright_red',
      more_data: typing.Optional[str] = None) -> None:

  import netsim.cli.validate as _validate
  record_result(f_status,msg)
  if _validate.TEST_HEADER:
    print(file=sys.stderr)
    p_status(_validate.TEST_HEADER['name'],'red',topology,stderr=True)
    print(_validate.TEST_HEADER['text'],file=sys.stderr)
    _validate.TEST_HEADER = {}

  o_file = sys.stderr if _validate.ERROR_ONLY else sys.stdout
  p_status(f_status,f_color,topology,stderr=_validate.ERROR_ONLY)
  print(msg,file=o_file)
  if more_data:
    p_status('MORE','bright_black',topology,stderr=_validate.ERROR_ONLY)
    print(more_data,file=o_file)

# Log a failure that stops the validation process
#
def log_abort(msg: str, topology: Box) -> None:
  import netsim.cli.validate as _validate
  _validate.RESULTS['reason'] = msg
  _validate.CURRENT.clear()                   # Not a test result
  log_failure(msg,topology)

# Print generic "making progress" message
#
def log_progress(msg: str, topology: Box, f_status: str = 'PASS') -> None:
  from . import ERROR_ONLY
  record_result(f_status,msg)
  if ERROR_ONLY:
    return

  p_status(f_status,'light_green',topology)
  print(msg)

# Print generic "ambivalent info" message
#
def log_info(msg: str, topology: Box, f_status: str = 'INFO', f_color: str = 'bright_cyan') -> None:
  from . import ERROR_ONLY
  record_result(f_status,msg)
  if ERROR_ONLY:
    return

  p_status(f_status,f_color,topology)
  print(msg)

# Print "test failed on node"
#
def p_test_fail(n_name: str, v_entry: Box, topology: Box, fail_msg: str = '') -> None:
  err = v_entry.get('fail',fail_msg or f'Test failed for node {n_name}')
  if n_name:
    err = f'Node {n_name}: '+err
  if v_entry.get('level') == 'warning':
    log_failure(err,topology,f_status='WARNING',f_color='bright_yellow')
  else:
    f_color = 'bright_yellow' if v_entry.get('_expect_fail',False) else 'bright_red'
    log_failure(err,topology,f_color=f_color)

# Print "test passed"
#
def p_test_pass(v_entry: Box, topology: Box) -> None:
  msg = v_entry.get('pass','Test succeeded')
  log_progress(msg,topology)

'''
test_plural: get "one test" or "x tests"
'''
def test_plural(cnt: int) -> str:
  return 'one test' if cnt == 1 else f'{cnt} tests'

def report_results(topology: Box) -> None:
  from . import TEST_COUNT
  print()
  if TEST_COUNT.passed == TEST_COUNT.count:
    log_progress(f'Tests passed: {TEST_COUNT.passed}',topology,f_status='SUCCESS')
  elif TEST_COUNT.count:
    if TEST_COUNT.failed != 0:
      log_failure(f'{test_plural(TEST_COUNT.count).capitalize()} completed, {test_plural(TEST_COUNT.failed)} failed',topology)
    elif TEST_COUNT.warning != 0:
      log_info(f'{test_plural(TEST_COUNT.warning).capitalize()} out of {test_plural(TEST_COUNT.count)} generated a warning',topology)
  if TEST_COUNT.skip:
    log_info(f'{test_plural(TEST_COUNT.skip).capitalize()} out of {test_plural(TEST_COUNT.count)} were skipped, the results are not reliable',topology)
