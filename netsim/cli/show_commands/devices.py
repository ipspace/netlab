#
# netlab show devices command -- display supported devices
#

import argparse

from box import Box

from ... import data
from ...utils import strings
from . import DEVICES_TO_SKIP, parser_add_device, show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('devices','supported devices')
  parser_add_device(parser)
  return parser

def print_result_table(result: Box, settings: Box) -> None:

  device_rows = []
  daemon_rows = []
  caveat_rows = []
  support_level = data.get_empty_box()

  heading = ['device','description','support level']
  for d_name in sorted(list(result)):
    d_data = result[d_name]
    support_text = d_data.get('support.level','✅') + (' ❗' if d_data.get('support.caveats') else '')
    row = [ d_name, d_data.description, support_text.center(len(heading[2])) ]
    d_support = d_data.get('support.level',None)
    if d_support:
      support_level[d_support] = True
    d_caveat = d_data.get('support.caveats',[])
    if d_caveat:
      caveat_rows.extend(d_caveat if isinstance(d_caveat,list) else [ d_caveat ])

    if d_data.get('daemon',False):
      daemon_rows.append(row)
    else:
      device_rows.append(row)

  if device_rows:
    strings.print_colored_text('Virtual network devices supported by netlab\n\n',color='bold')
    strings.print_table(heading,device_rows,inter_row_line=False)

  if daemon_rows:
    strings.print_colored_text('\nNetworking daemons supported by netlab\n\n',color='bold')
    heading[1] = 'daemon'
    strings.print_table(heading,daemon_rows,inter_row_line=False)

  if support_level:
    strings.print_colored_text('\nLegend: support levels\n\n',color='bold')
    for sl in sorted(list(support_level)):
      print(strings.wrap_error_message(f'* {sl}: {settings.hints.support[sl]}',indent=2))

  if caveat_rows:
    strings.print_colored_text('\nCaveats:\n\n',color='bold')
    for cv in caveat_rows:
      print(strings.wrap_error_message(f'* {cv}',indent=2))

def show(settings: Box, args: argparse.Namespace) -> None:
  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    dev_data = settings.devices[device]
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    dev_summary = data.get_box({ 'description': dev_data.description })
    if 'support' in dev_data:
      dev_summary.support = dev_data.support
    if dev_data.daemon:
      dev_summary.daemon = True
      dev_summary.parent = dev_data.daemon_parent

    result[device] = dev_summary

  if args.format == 'table':
    print_result_table(result,settings)

  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
