#
# 'netlab show' commands
#

import argparse
from box import Box

from ...utils import log

DEVICES_TO_SKIP = ['none','unknown']

def parser_add_device(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-d','--device',
    dest='device',
    action='store',
    default='*',
    help='Display information for a single device')

def parser_add_module(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-m','--module',
    dest='module',
    action='store',
    help='Display information for a single module')

def show_common_parser(action: str, content: str) -> argparse.ArgumentParser:
  global show_dispatch
  parser = argparse.ArgumentParser(
    prog=f'netlab show {action}',
    description=f'Display {content}')
  parser.add_argument(
    '--system',
    dest='system',
    action='store_true',
    help='Display system information (without user defaults)')
  parser.add_argument(
    '--format',
    dest='format',
    action='store',
    choices=['table','text','yaml'],
    default='table',
    help='Output format (table, text, yaml)')
  return parser

def get_modlist(settings: Box, args: argparse.Namespace) -> list:
  if args.module:
    if settings[args.module].supported_on:
      return [ args.module ]
    else:
      log.fatal(f'Unknown module: {args.module}')
    
  return sorted([ m for m in settings.keys() if 'supported_on' in settings[m]])
