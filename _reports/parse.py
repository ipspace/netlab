#!/usr/bin/env python3
#
import argparse
import typing
from box import Box

from netsim.cli import parser_add_verbose
from netsim.utils.log import fatal

def parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace,typing.List[str]]:
  parser = argparse.ArgumentParser(
    description='Created summary reports from automated integration tests')
  parser.add_argument(
    dest='action',
    action='store',
    choices=['html','yaml','errors','release'],
    help='Specify the report type')

  parser_add_verbose(parser)

  return parser.parse_known_args(args)

def no_extra_args(action: str, x_args: list) -> None:
  if not x_args:
    return
  
  fatal(f'Action {action} does not recognize additional arguments')
