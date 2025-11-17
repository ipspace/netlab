#!/usr/bin/env python3
#
import datetime
import typing
import argparse
from box import Box

from netsim.utils.log import fatal
from netsim.data import get_empty_box,append_to_list

def parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace,typing.List[str]]:
  parser = argparse.ArgumentParser(
    description='Report recent tests')
  parser.add_argument(
    '--device',
    dest='device',
    action='store_true',
    help='Display only the tested devices')
  parser.add_argument(
    '--test',
    dest='test',
    action='store_true',
    help='Display tested devices and tests that were run')
  parser.add_argument(
    '-i','--interval',
    dest='interval',
    action='store',
    type=int,
    default='24',
    help='Recent interval in hours (default: 24)')
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
    if results[k] is False or (results[k] == 'warning' and args.warning):
      if k in ['create','supported']:
        continue
      if k == 'validate' and 'caveat' in results and not args.ignore_caveats:
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

def print_recent(
      path: str,
      results: Box,
      timestamp: str,
      device: bool = False,
      test: bool = False,
      silent: bool = False) -> bool:

  if not isinstance(results,Box):
    return False

  if device:
    for k in results.keys():
      if print_recent(k,results[k],timestamp,silent=True):
        print(f'{path}.{k}' if path else k)
    return False
  
  if test:
    recent = False
    for d in results.keys():
      if isinstance(results[d],Box):
        for p in results[d].keys():
          recent = print_recent(d,results[d][p],timestamp,device=True) or recent
    return recent

  recent = False
  for k in results.keys():
    if not isinstance(results[k],Box):
      continue
    elif '_timestamp' in results[k]:
      if results[k]._timestamp > timestamp:
        recent = True
        if not silent:
          print(f'{path}.{k}')
    else:
      recent = print_recent(f'{path}.{k}' if path else k,results[k],timestamp,silent=silent) or recent

  return recent

def create(x_args: typing.List[str], results: Box) -> None:
  global SUMMARY
  (args,x_args) = parse(x_args)

  recent_ts = str(datetime.datetime.now() - datetime.timedelta(hours=args.interval))
  if not x_args:
    print_recent('',results,timestamp=recent_ts,device=args.device,test=args.test)
    return

  if args.device or args.test:
    fatal('Cannot use --device or --test with test selector')
  for selector in x_args:
    if selector not in results:
      fatal(f'Cannot find {selector} in test results')
    print_recent(selector,results[selector],timestamp=recent_ts)
