#
# netlab validate command
#
# Perform lab validation tests
#
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

'''
list_tests: display validation tests defined for the current lab topology
'''
def list_tests(topology: Box) -> None:
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
Main routine: run all tests, handle validation errors, print summary results
'''
def run(cli_args: typing.List[str]) -> None:
  global TEST_COUNT,ERROR_ONLY
  args = parse.validate_parse(cli_args)
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

    if result is False:
      if v_entry.stop_on_error:
        print()
        report.log_failure('Mandatory test failed, validation stopped',topology)
        sys.exit(1)

    if 'wait' in v_entry:
      start_time = time.time()

    cnt = cnt + 1

  if not ERROR_ONLY:
    report.report_results(topology)

  sys.exit(0 if not (TEST_COUNT.failed or TEST_COUNT.warning) else 1 if TEST_COUNT.failed else 3)
