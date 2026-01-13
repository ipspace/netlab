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

def print_recent(
      path: str,
      results: Box,
      timestamp: str,
      device: bool = False,
      test: bool = False,
      silent: bool = False) -> int:

  if not isinstance(results,Box):
    return 0

  sum_recent = 0
  if device:
    for k in results.keys():
      d_recent = print_recent(k,results[k],timestamp,silent=True)
      sum_recent += d_recent
      if d_recent:
        d_path = f'{path}.{k}' if path else k
        print(f'{d_path:30s} {d_recent}')
    return sum_recent
  
  if test:
    for d in results.keys():
      if isinstance(results[d],Box):
        for p in results[d].keys():
          d_recent = print_recent(d,results[d][p],timestamp,device=True)
          sum_recent += d_recent
    return sum_recent

  for k in results.keys():
    if not isinstance(results[k],Box):
      continue
    elif '_timestamp' in results[k]:
      if results[k]._timestamp > timestamp:
        sum_recent += 1
        if not silent:
          print(f'{path}.{k}')
    else:
      t_recent = print_recent(f'{path}.{k}' if path else k,results[k],timestamp,silent=silent)
      sum_recent += t_recent

  return sum_recent

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
