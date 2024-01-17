#
# netlab show devices command -- display supported devices
#

import argparse
from box import Box

from ...utils import strings
from ... import data
from . import show_common_parser,parser_add_device,DEVICES_TO_SKIP

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('devices','supported devices')
  parser_add_device(parser)
  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device','description']

  rows = []
  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    dev_data = settings.devices[device]
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    row = [ device,dev_data.description ]
    if dev_data.daemon:
      row[1] = {
        'daemon': True,
        'description': dev_data.description,
        'parent': dev_data.daemon_parent
      }
    rows.append(row)
    result[device] = row[1]

  if args.format == 'table':
    print('Virtual network devices supported by netlab')
    print("")
    strings.print_table(heading,[ r for r in rows if isinstance(r[1],str) ],inter_row_line=False)
    daemons = [ [ r[0],r[1]['description']] for r in rows if isinstance(r[1],dict) and r[1]['daemon'] ]
    if daemons:
      print('\nNetworking daemons supported by netlab\n')
      strings.print_table(['daemon','description'],daemons,inter_row_line=False)

  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
