#
# netlab validate command
#
# Perform lab validation tests
#
import argparse
import datetime
import json
import os
import sys
import time
import traceback
import typing

from box import Box

from ...data import get_box
from ...utils import log, strings
from ...utils import status as _status
from .. import load_snapshot
from . import parse, report, source, tests

# I'm cheating. Declaring a global variable is easier than passing 'args' argument around
#
ERROR_ONLY: bool = False
TEST_HEADER: dict = {}
TEST_COUNT: Box = get_box({'passed': 0, 'failed': 0, 'warning': 0, 'count': 0, 'skip': 0})

# JSON output: results format, current test/node context, and the data collected for the
# JSON printout (start time, per-test results, test list, completion flag, abort reason)
#
RESULT_FORMAT: str = 'text'
CURRENT: dict = {}
RESULTS: dict = { 'results': {} }

'''
list_tests: display validation tests defined for the current lab topology
'''
def list_tests(topology: Box) -> None:
  if RESULT_FORMAT == 'json':                     # Save the test list for the JSON printout
    RESULTS['tests'] = {
      v_entry.name: {
        'description': v_entry.get('description',None),
        'nodes': list(v_entry.nodes),
        'devices': list(v_entry.devices),
        'wait': v_entry.get('wait',None) }
      for v_entry in topology.validate }
    return

  heading = [ 'Test','Description','Nodes','Devices','Wait' ]
  rows = [
    [ v_entry.name,
      v_entry.description or '',
      ",".join(v_entry.nodes),
      ",".join(v_entry.devices),
      str(v_entry.get('wait','')) ]
    for v_entry in topology.validate ]
  strings.print_table(heading,rows)

'''
Main routine: parse the arguments, run the tests (with or without JSON results)
'''
def run(cli_args: typing.List[str]) -> None:
  global RESULT_FORMAT
  args = parse.validate_parse(cli_args)
  RESULT_FORMAT = args.format
  if RESULT_FORMAT == 'json':
    run_json(args)
  else:
    run_validation(args)

'''
run_json: run the tests with stdout (including subprocess output) redirected to /dev/null,
and print the JSON results on the real stdout when the validation process exits
'''
def run_json(args: argparse.Namespace) -> None:
  RESULTS['started'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
  sys.stdout.flush()
  saved_fd = os.dup(1)                            # Keep the real stdout for the JSON printout
  null_fd = os.open(os.devnull,os.O_WRONLY)
  os.dup2(null_fd,1)                              # ... and send everything else into a black hole
  os.close(null_fd)                               # ... including subprocess output
  saved_stdout = sys.stdout
  sys.stdout = open(os.devnull,'w')               # ... and Python printouts (in case sys.stdout is not fd 1)

  exit_code: typing.Optional[int] = None
  try:
    run_validation(args)                          # Returns only when listing the tests
  except SystemExit as ex:
    exit_code = ex.code if isinstance(ex.code,int) else 1
    raise
  finally:
    sys.stdout.close()                            # Restore stdout
    sys.stdout = saved_stdout
    os.dup2(saved_fd,1)
    os.close(saved_fd)
    if exit_code is not None:
      print(json.dumps(report.json_results(exit_code),indent=2))
    elif 'tests' in RESULTS:
      print(json.dumps({ 'version': report.JSON_VERSION, 'tests': RESULTS['tests'] },indent=2))
    sys.stdout.flush()

'''
run_validation: run all tests, handle validation errors, print summary results
'''
def run_validation(args: argparse.Namespace) -> None:
  global TEST_COUNT,ERROR_ONLY
  if args.error_only:
    args.quiet = True
  log.set_logging_flags(args)
  topology = load_snapshot(args,warn_modified=False)
  if args.test_source:
    source.update_validation_tests(topology,args.test_source)
  elif topology.get('_input.modified'):
    log.warning(
      text=f'Topology source file(s) have changed since the lab has started',
      module='-')
    source.update_validation_tests(topology,topology.input[0])

  if 'validate' not in topology:
    if args.skip_missing:
      RESULTS['reason'] = 'No validation tests defined for the current lab'
      sys.exit(2)
    else:
      log.fatal('No validation tests defined for the current lab, exiting')

  parse.filter_by_tests(args,topology)
  parse.filter_by_nodes(args,topology)
  log.exit_on_error()
  topology._v_len = max([ len(v_entry.name) for v_entry in topology.validate ] + [ 7 ])
  tests.extend_first_wait_time(args,topology)

  if args.list:
    list_tests(topology)
    return

  ERROR_ONLY = args.error_only
  cnt = 0
  start_time = _status.lock_timestamp() or time.time()
  log.init_log_system(header=False)

  for v_entry in topology.validate:
    tests.extend_device_wait_time(v_entry,topology)
    if cnt and not ERROR_ONLY:
      print()

    try:
      result = tests.execute_validation_test(v_entry,topology,start_time,args)
    except KeyboardInterrupt:
      print("")
      log.fatal('Validation test interrupted')
    except SystemExit:
      sys.exit(1)
    except Exception:
      traceback.print_exc()
      log.fatal('Unhandled exception')

    CURRENT.clear()                                 # Test done, stop collecting its results
    if result is False:
      if v_entry.stop_on_error:
        print()
        report.log_abort('Mandatory test failed, validation stopped',topology)
        sys.exit(1)

    if 'wait' in v_entry:
      start_time = time.time()

    cnt = cnt + 1

  if not ERROR_ONLY:
    report.report_results(topology)

  RESULTS['completed'] = True
  sys.exit(0 if not (TEST_COUNT.failed or TEST_COUNT.warning) else 1 if TEST_COUNT.failed else 3)
