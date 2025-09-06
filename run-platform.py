#!/usr/bin/env python3
#
import argparse
import typing
import sys
import os
import time
import pathlib

from box import Box

import netsim.utils.read as _read
import netsim.utils.log as log
import netsim.utils.strings as _strings
import netsim.data as _data
from netsim.cli.external_commands import run_command

def tests_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Run platform integration tests')
  parser.add_argument(
    '-t','--tests',
    dest='tests',
    action='store',
    help='Run only these test suite(s)')
  parser.add_argument(
    '-s','--skip-tests',
    dest='skip',
    action='store',
    help='Skip these tests')
  parser.add_argument(
    '--limit',
    dest='limit',
    action='store',
    help='Select a subset of tests in a single test suite')
  parser.add_argument(
    '--dry-run',
    dest='dryrun',
    action='store_true',
    help='Do a dry run (print the commands that would be executed)')

  return parser.parse_args(args)

def check_valid_tests(setup: Box, t_list: list) -> None:
  for test in t_list:
    if test not in setup.tests.keys():
      log.fatal(f'Unknown integration test {test}',module='tests')

def build_test_list(setup: Box) -> None:
  setup.tests = {}
  test_suites = pathlib.Path(setup.params.platform_path).expanduser()
  for ts_name in test_suites.glob('*'):
    if not ts_name.is_dir():
      continue

    if ts_name.glob('[0-9]*.yml'):
      setup.tests[ts_name.name] = {}

def prune_setup(setup: Box, args: argparse.Namespace) -> None:
  if args.tests:
    x_tests = args.tests.split(',')
    for idx,test in enumerate(x_tests):
      if ':' in test:
        t_components = test.split(':')
        x_tests[idx] = t_components[0]
        setup.limits[x_tests[idx]] = t_components[1]

    check_valid_tests(setup,x_tests)
    setup.tests = { k:v for k,v in setup.tests.items() if k in x_tests }

  if args.skip:
    s_tests = args.skip.split(',')
    check_valid_tests(setup,s_tests)
    setup.tests = { k:v for k,v in setup.tests.items() if k not in s_tests }

  for ev in os.environ.keys():
    if not ev.startswith('CICD_'):
      continue
    param = ev.replace('CICD_','').lower()
    setup.params[param] = os.environ[ev]

def run_single_test(
      test: str,
      limit: typing.Optional[str],
      setup: Box,
      dry_run: bool = False) -> bool:
  print()
  if not dry_run:
    _strings.print_colored_text('[RUNNING]    ',color='green')
    print(f'Platform test suite: {test} Limit: {limit} (abort with ctrl/c)')
    _strings.print_colored_text('[LASTCHANCE] ',color='green')
    print('Abort with CTRL/C')
    print()
    time.sleep(1)

#  os.environ['NETLAB_GROUPS_ALL_VARS_NETLAB__SHOW__CONFIG'] = 'True'  # Enable configuration display
  for nl_param in setup.netlab.keys():
    ev = 'NETLAB_' + nl_param.upper()
    if ev not in os.environ:
      os.environ[ev] = str(setup.netlab[nl_param])
      print(f'Set: {ev}={os.environ[ev]}')

  log_path = os.path.expanduser(setup.params.log or setup.params.home) + '/platform/' + test
  workdir  = setup.params.workdir or '/tmp/netlab_cicd'
  print(f'Running in {workdir}, logging to {log_path}')
  pwd = os.getcwd()
  os.chdir(os.path.expanduser(setup.params.platform_path))
  script_path = os.path.expanduser(setup.params.test_path)
  cmd = [ f'{script_path}/device-module-test', test, '--workdir', workdir, '--logdir', log_path, '--batch', '--platform' ]
  if limit:
    cmd += [ '--redo', limit ]
  if dry_run:
    print(f'DRY RUN: {cmd}')
  else:
    run_command(cmd,ignore_errors=True)
  os.chdir(pwd)

  return True

def run_tests(setup: Box, limit: typing.Optional[str], dry_run: bool = False) -> None:
    for test in setup.tests:
      run_single_test(test,
        limit=limit or setup.limits[test] or None,
        setup=setup,
        dry_run=dry_run)

def main() -> None:
  args = tests_parse(sys.argv[1:])
  setup = _read.load('setup.yml')
  build_test_list(setup)
  prune_setup(setup,args)
  for n_env in ['NETLAB_DEVICE','NETLAB_PROVIDER']:
    if n_env in os.environ:
      _strings.print_colored_text('[CLEANUP]    ',color='green')
      print(f'Removing environment variable {n_env}')
      os.environ.pop(n_env,None)                      # Remove environment variables that could impact the tests

  try:
    run_tests(setup,args.limit,args.dryrun)
  except KeyboardInterrupt as ex:
    print('\nAborted by keyboard interrupt')

if __name__ == '__main__':
  main()
