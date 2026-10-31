#
# netlab show tools command -- display external tools
#

import argparse

from box import Box

from ... import data
from ...utils import log, strings
from .utils import show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('tools','external tools that can be started with the lab')
  parser.add_argument(
    '-t','--tool',
    dest='tool',
    action='store',
    help='Display information for a single tool')

  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  heading = ['tool','description','runtime','enabled']

  if args.tool and args.tool not in settings.tools:
    log.fatal(f'Unknown tool {args.tool}, use "netlab show tools" to list valid tools')

  rows = []
  result = data.get_empty_box()
  for tname in sorted(settings.tools.keys()):
    if args.tool and tname != args.tool:
      continue

    tdata = settings.tools[tname]
    runtimes = [                                            # A runtime is a dictionary with the 'up' command
      rt for rt,rt_data in tdata.items() if isinstance(rt_data,Box) and 'up' in rt_data ]
    enabled = tdata.get('enabled',False) is True            # Tools can be enabled in user defaults
    rows.append([ tname,tdata.description or '',tdata.runtime or '',"yes" if enabled else "" ])
    result[tname] = {
      'description': tdata.description or '',
      'runtime': tdata.runtime or '',
      'runtimes': runtimes,
      'enabled': enabled }

  if args.format == 'table':
    print('External tools supported by netlab')
    print("")
    strings.print_table(heading,rows,inter_row_line=False)
  elif args.format == 'text':
    for tname,tdata in result.items():
      print(f"{tname} ({tdata.description}): {tdata.runtime}{', enabled' if tdata.enabled else ''}")
  else:
    print(strings.get_yaml_string(result))
