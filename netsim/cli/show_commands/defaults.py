#
# netlab show attributes -- display supported attributes
#

import argparse
import typing
import textwrap
from box import Box

from ...utils import strings,log
from ... import data
from . import show_common_parser,parser_add_module,DEVICES_TO_SKIP,get_modlist

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('defaults','(a subset) of system/user defaults')
  parser.add_argument(
    nargs='?',
    default='',
    dest='match',
    action='store',
    help='Display defaults within the specified subtree')
  parser.add_argument(
    '--plugin',
    nargs='+',
    dest='plugin',
    action='store',
    help='Add plugin attributes to the system defaults')
  parser.add_argument(
    '--evaluate-paths',
    dest='eval_paths',
    action='store_true',
    help='Evaluate system search paths before displaying them')

  return parser

def get_attribute_subset(settings: Box, args: argparse.Namespace) -> typing.Optional[Box]:
  if not args.match:
    return settings
  
  return settings.get(args.match,None)

def show(settings: Box, args: argparse.Namespace) -> None:
  if not args.eval_paths:                         # If the user doesn't want to see the transformed paths
    settings.paths = settings._original_paths     # ... restore the paths saved by the parent CLI handling code

  settings.pop('_original_paths',None)            # ... and make sure the temporary dictionary is not displayed
                                                  # ... with the system defaults
  show = get_attribute_subset(settings, args)
  if show is None:
    log.fatal(f'There are no system/user defaults within the {args.match} subtree')

  if args.format in ['text','table']:
    print(f"""
netlab default settings {"within the "+args.match+" subtree" if args.match else ""}
=============================================================================
""")
  elif args.format == 'yaml':
    print('---')

  print(strings.get_yaml_string(show))
