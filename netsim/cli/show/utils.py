#
# 'netlab show' commands
#

import argparse
import math
import typing

from box import Box

from ...utils import log

DEVICES_TO_SKIP: typing.List[str] = []

def parser_add_device(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-d','--device',
    dest='device',
    action='store',
    default='*',
    help='Display information for a single device')

def parser_add_provider(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-p','--provider',
    dest='provider',
    action='store',
    help='Display information for a single virtualization provider')

def parser_add_module(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-m','--module',
    dest='module',
    action='store',
    help='Display information for a single module')

def show_empty_parser(action: str, content: str, system_only: bool = True) -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog=f'netlab show {action}',
    description=f'Display {content}')
  if system_only:
    parser.add_argument(
      '--system',
      dest='system',
      action='store_true',
      help='Display system information (without user defaults)')
  return parser

def show_common_parser(action: str, content: str, system_only: bool = True) -> argparse.ArgumentParser:
  parser = show_empty_parser(action, content, system_only)
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

# The "split_table" function is a generator that yields subsets of table headings
# no longer than max_column. It returns:
#
# * A single entry when the input list short enough
# * A sequence of balanced entries for longer lists
#
def split_table(f_list: list, max_column: int) -> typing.Generator:
  fl_len = len(f_list)
  if fl_len <= max_column:
    yield(f_list)
    return

  # Calculate the number of tables we need and the number of columns in each
  # table. The number of tables is easy to calculate (we need at least
  # list_len/columns tables), the number of columns is unchanged when it cleanly
  # divides the list length (just in case to avoid floating point errors),
  # otherwise it's rounded up from the average number of columns per table.
  #
  num_tables = math.ceil(fl_len/max_column)
  cols = max_column if fl_len % max_column == 0 else math.floor(fl_len / num_tables)
  while f_list:                                   # More work to do?
    cols = min(cols,len(f_list))                  # Return at most "cols" columns
    yield(f_list[:cols])                          # (note: the "cols" value changes only on last iteration)
    f_list = f_list[cols:]                        # ... and shorten the input list

  return
