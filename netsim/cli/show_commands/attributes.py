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
  parser = show_common_parser('attributes','supported global- or module-specific attributes')
  parser_add_module(parser)
  parser.add_argument(
    nargs='?',
    default='',
    dest='match',
    action='store',
    help='Display a subset of attributes')
  parser.add_argument(
    '--plugin',
    nargs='+',
    dest='plugin',
    action='store',
    help='Add plugin attributes to the system defaults')

  return parser

def get_attribute_subset(settings: Box, args: argparse.Namespace) -> Box:
  if not args.match and not args.module:
    return settings.attributes

  show = settings
  link_no_propagate = settings.attributes.link_no_propagate
  if args.module:
    if args.module in show and 'attributes' in show[args.module]:
      show = show[args.module]
    else:
      log.fatal(f"Unknown module {args.module} -- use netlab show modules to display known modules")

  if not args.match:
    return data.get_box({ k:v for k,v in show.attributes.items() if isinstance(v,dict) })  # Remove non-attribute parts
  
  if not args.match in show.attributes:
    log.fatal(f"Unknown attribute type {args.match} -- use less-specific show command to display valid attribute types")

  if args.match == 'interface' and not args.module:      # Add propagatable global link attributes to interface attributes
    link_propagate =  { 
      k:v for k,v in show.attributes['link'].items() 
        if not k in link_no_propagate }
    show = link_propagate + show.attributes[args.match]
  else:
    show = show.attributes[args.match]
  
  return show

def show(settings: Box, args: argparse.Namespace) -> None:
  show = get_attribute_subset(settings, args)

  ns = None
  if args.format in ['text','table']:
    hline = "=" * 78
    ns = show.pop('_namespace',None)
    if '_description' in show:
      print(f'{show._description}\n{hline}')
      show.pop('_description',None)
    else:
      print(f"""
You can use the following {args.module or 'global'}{" "+args.match if args.match else ""} {'' if args.module else 'lab topology '}attributes:
{hline}
""")

  if args.format == 'yaml':
    print('---')

  print(strings.get_yaml_string(show))

  if args.format in ['text','table']:
    if ns:
      print(f"You can also use {','.join(ns)} attributes with this object")

    print(
f"""{hline}
See https://netlab.tools/dev/validation/ for more data type- and
attribute validation details.
""")
