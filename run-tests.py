#!/usr/bin/env python3
#
import argparse
import typing
import sys
import os
import time

from box import Box

import netsim.utils.read as _read
import netsim.utils.log as log
import netsim.utils.strings as _strings
import netsim.augment.devices as devices
from netsim.cli.external_commands import run_command

def tests_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Run integration tests')
  parser.add_argument(
    '--all',
    dest='all',
    action='store_true',
    help='Run tests for all devices')
  parser.add_argument(
    '-d','--device',
    dest='device',
    action='store',
    help='Limit tests to a single device')
  parser.add_argument(
    '-x','--exclude',
    dest='exclude',
    action='store',
    help='Exclude devices from tests')
  parser.add_argument(
    '-s','--skip-tests',
    dest='skip',
    action='store',
    help='Skip some tests (equivalent to -x for devices)')
  parser.add_argument(
    '-p','--provider',
    dest='provider',
    action='store',
    help='Limit tests to a single provider')
  parser.add_argument(
    '-t','--tests',
    dest='tests',
    action='store',
    help='Limit tests to a single test suite')
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

def prune_setup(setup: Box, args: argparse.Namespace) -> None:
  if not args.all and not args.device:
    log.fatal('You have to specify the devices to test, using either --device or --all flag',module='tests')

  if args.device:
    i_devices = args.device.split(',')
    for device in i_devices:
      if device not in setup.devices.keys():
        log.fatal(f'We have not configured integration tests for device {args.device}',module='tests')

    setup.devices = { k:v for k,v in setup.devices.items() if k in i_devices }

  elif args.exclude:
    x_devices = args.exclude.split(',')
    setup.devices = { k:v for k,v in setup.devices.items() if k not in x_devices }

  if args.provider:
    valid = False
    for dname in list(setup.devices.keys()):
      if args.provider in setup.devices[dname]:
        setup.devices[dname] = { args.provider: setup.devices[dname][args.provider] }
        valid = True
      else:
        setup.devices.pop(dname,None)
    if not valid:
      log.fatal(f'Provider {args.provider} is not used in any integration tests',module='tests')

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

  for test in list(setup.tests.keys()):
    if setup.tests[test] is None:
      setup.tests[test] = {}
    for kw in ('supports','path'):
      if not kw in setup.tests[test]:
        setup.tests[test][kw] = test

  for ev in os.environ.keys():
    if not ev.startswith('CICD_'):
      continue
    param = ev.replace('CICD_','').lower()
    setup.params[param] = os.environ[ev]

def include_test(dp_data: typing.Optional[Box], test: str) -> bool:
  if dp_data is None:
    return True
  if not isinstance(dp_data,Box):
    return True
  
  if 'include' in dp_data:
    return test in dp_data.include
  
  if 'exclude' in dp_data:
    return test not in dp_data.exclude
  
  return True

def device_supports_test(device: str, t_data: Box, setup: Box) -> bool:
  d_features = setup.defaults.devices[device].features or setup.defaults.daemons[device].features
  rq_feature = t_data.supports or 'missing'

  if rq_feature not in d_features:
    print(f'Device {device} does not support {rq_feature}, skipping')
    return False
  
  return True

def run_single_test(
      device: str,
      provider: str,
      test: str,
      limit: typing.Optional[str],
      setup: Box,
      dry_run: bool = False) -> bool:
  print()
  if not dry_run:
    _strings.print_colored_text('[RUNNING]    ',color='green')
    print(f'Device: {device} Provider: {provider} Test suite: {test} Limit: {limit} (abort with ctrl/c)')
    _strings.print_colored_text('[LASTCHANCE] ',color='green')
    print('Abort with CTRL/C')
    print()
    time.sleep(1)

  os.environ['NETLAB_DEVICE'] = device
  os.environ['NETLAB_PROVIDER'] = provider
  os.environ[f'NETLAB_DEVICES_{device}_PROVIDER'] = provider          # Force device-specific provider
  os.environ['NETLAB_GROUPS_ALL_VARS_NETLAB__SHOW__CONFIG'] = 'True'  # Enable configuration display
  for nl_param in setup.netlab.keys():
    ev = 'NETLAB_' + nl_param.upper()
    if ev not in os.environ:
      os.environ[ev] = str(setup.netlab[nl_param])
      print(f'Set: {ev}={os.environ[ev]}')

  log_path = os.path.expanduser(setup.params.log or setup.params.home) + '/' + device + '/' + provider + '/' + test
  workdir  = setup.params.workdir or '/tmp/netlab_cicd'
  print(f'Running in {workdir}, logging to {log_path}')
  pwd = os.getcwd()
  os.chdir(os.path.expanduser(setup.params.test_path))
  cmd = [ './device-module-test', test, '--workdir', workdir, '--logdir', log_path, '--batch' ]
  if limit:
    cmd += [ '--redo', limit ]
  if dry_run:
    print(f'DRY RUN: {cmd}')
  else:
    run_command(cmd,ignore_errors=True)
  os.chdir(pwd)

  return True

def run_tests(setup: Box, limit: typing.Optional[str], dry_run: bool = False) -> None:
  for device in setup.devices:
    for provider in setup.devices[device]:
      for test in setup.tests:
        if limit is None and test in setup.limits:
          limit = setup.limits[test]
        if not include_test(setup.devices[device][provider],test):
          continue
        if not device_supports_test(device,setup.tests[test],setup):
          continue
        run_single_test(device,provider,setup.tests[test].path,limit,setup=setup,dry_run=dry_run)

def main() -> None:
  args = tests_parse(sys.argv[1:])
  setup = _read.load('setup.yml')
  devices.augment_device_settings(setup)
  prune_setup(setup,args)
#  print(setup.to_yaml())

  try:
    run_tests(setup,args.limit,args.dryrun)
  except KeyboardInterrupt as ex:
    print('\nAborted by keyboard interrupt')

if __name__ == '__main__':
  main()
