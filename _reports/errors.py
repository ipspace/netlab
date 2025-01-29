#!/usr/bin/env python3
#
import typing
import argparse
from box import Box

from netsim.utils.log import fatal
from netsim.data import get_empty_box,append_to_list

def parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace,typing.List[str]]:
  parser = argparse.ArgumentParser(
    description='Created error reports from automated integration tests')
  parser.add_argument(
    '--rerun',
    dest='rerun',
    action='store_true',
    help='Create "rerun test" instructions')
  parser.add_argument(
    '--oneline',
    dest='oneline',
    action='store_true',
    help='Create one-line "rerun test" instructions')
  parser.add_argument(
    '--summary',
    dest='summary',
    action='store_true',
    help='Create summary failure report')
  parser.add_argument(
    '--report',
    dest='report',
    action='store_true',
    help='Create summary failure report')
  parser.add_argument(
    '--caveats',
    dest='caveats',
    action='store_true',
    help='Create caveats data structure')

  return parser.parse_known_args(args)

SUMMARY: Box = get_empty_box()

def sum_failure(path: str) -> None:
  global SUMMARY
  components = path.split('.')
  if len(components) < 4:
    fatal(f'Cannot add {path} to failure summary')

  device = components[0]
  test_suite = components[-2].replace('#','_')
  append_to_list(SUMMARY,device,test_suite)

def print_summary(summary: Box) -> None:
  for k,v in summary.items():
    if isinstance(v,list):
      print(f'{k}: {" ".join(v)}')
    else:
      print(f'{k}: {v}')

def print_rerun_instructions(path: str,args: argparse.Namespace) -> None:
  components = path.split('.')
  if len(components) < 4:
    fatal(f'Cannot create rerun instructions for {path}')

  device = components[0]
  provider = components[1]
  test_suite = components[-2].replace('#','_')
  limit = components[-1].split('-')[0]
  separator = '; ' if args.oneline else '\n'
  print(f'./run-tests.py -d {device} -p {provider} -t {test_suite} --limit {limit}',end=separator)

def print_caveats(path: str) -> None:
  components = path.split('.')
  if len(components) < 3:
    fatal(f'Cannot create caveats for {path}')

  for idx,value in enumerate(components[2:]):
    print (" " * idx * 2 + value + ":")
    if idx == len(components) - 3:
      print(" " * (idx + 1) * 2 + "caveat: |\n")

def print_report(path: str, fail_step: str) -> None:
  components = path.split('.')
  test_url = "https://github.com/ipspace/netlab/blob/dev/tests/integration/"
  result_url = "https://tests.netlab.tools/"
  print(f'{components[-1].split(".")[0]}:')
  print(f'* [Test topology]({test_url}{"/".join(components[2:])}.yml)')
  print(f'* [Test results]({result_url}{"/".join(components)}.yml-{fail_step}.log)')
  print()

def check_test_result(path: str, results: Box, args: argparse.Namespace) -> bool:
  fail_step = None
  for k in results.keys():
    if results[k] is False:
      if k in ['create','supported']:
        continue
      if k == 'validate' and 'caveat' in results:
        continue

      fail_step = k
      xkw = [ kw for kw in ['rerun','summary','caveats','report'] if vars(args)[kw] ]
      if not xkw:
        print(f'{path}: {k}')

  if fail_step is None:
    return True
  
  if args.summary:
    sum_failure(path)
  if args.rerun:
    print_rerun_instructions(path,args)
  if args.caveats:
    print_caveats(path)
  if args.report:
    print_report(path,fail_step)

  return False

def print_errors(path: str, results: Box, args: argparse.Namespace) -> typing.Optional[bool]:
  if '_count' not in results and path:
    return check_test_result(path,results,args)

  test_ok = None
  for k in results.keys():
    if not k:
      continue
    if k.startswith('_'):
      continue
    if not isinstance(results[k],Box):
      continue

    if print_errors(f'{path}.{k}' if path else k,results[k],args) is False:
      test_ok = False

  return test_ok

def create(x_args: typing.List[str], results: Box) -> None:
  global SUMMARY
  (args,x_args) = parse(x_args)

  if not x_args:
    print_errors('',results,args)

  for selector in x_args:
    if selector not in results:
      fatal(f'Cannot find {selector} in test results')
    if print_errors(selector,results[selector],args) is False:
      if args.oneline:
        print()

  if args.summary:
    print_summary(SUMMARY)
