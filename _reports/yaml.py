#!/usr/bin/env python3
#
import typing
import argparse
from box import Box

from netsim.utils.log import fatal

def parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace,typing.List[str]]:
  parser = argparse.ArgumentParser(
    description='Extract YAML data from automated integration tests')
  parser.add_argument(
    '-k','--keys',
    dest='keys',
    action='store_true',
    help='Print just the keys')

  return parser.parse_known_args(args)

def print_info(results: Box, args: argparse.Namespace) -> None:
  if args.keys:
    print(list(results.keys()))
  else:
    print(results.to_yaml())

def create(x_args: typing.List[str], results: Box) -> None:
  (args,x_args) = parse(x_args)

  if not x_args:
    print_info(results,args)
  for selector in x_args:
    if selector not in results:
      fatal(f'Cannot find {selector} in test results')
    
    if len(x_args) > 1:
      print("=" * 80,"\n",selector,"\n","=" * 80)

    print_info(results[selector],args)
