#
# Reporting functions for the "netlab validate" command
#
import sys
import typing

from box import Box

from ...utils import strings

'''
increase_fail_count, increase_pass_count: Increase the counters based on test severity level
'''
def increase_fail_count(v_entry: Box) -> None:
  from . import TEST_COUNT
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

# Print generic "making progress" message
#
def log_progress(msg: str, topology: Box, f_status: str = 'PASS') -> None:
  from . import ERROR_ONLY
  if ERROR_ONLY:
    return

  p_status(f_status,'light_green',topology)
  print(msg)

# Print generic "ambivalent info" message
#
def log_info(msg: str, topology: Box, f_status: str = 'INFO', f_color: str = 'bright_cyan') -> None:
  from . import ERROR_ONLY
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
    log_failure(err,topology)

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
