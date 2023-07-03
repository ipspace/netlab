#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import textwrap
from box import Box

from .. import common
from .. import read_topology
from .. import data

DEVICES_TO_SKIP = ['none','unknown']

def print_table(
      heading: typing.List[str],
      rows: typing.List[typing.List[str]],
      inter_row_line: bool = True) -> None:

  col_len: typing.List[int] = []

  def print_row(separator: str, row: typing.Optional[list] = None, char: str = ' ') -> None:
    line = separator
    for idx,clen in enumerate(col_len):
      if row:
        value = ' ' + row[idx] + (' ' * 80)
      else:
        value = char * (clen + 2)
      line = line + value[:clen+2] + separator
    print(line)

  for idx,data in enumerate(heading):
    slice_len = [ len(k[idx]) for k in rows ]
    slice_len.append(len(heading[idx]))
    col_len.append(max(slice_len))

  print_row('+',char='-')
  print_row('|',row=heading)
  print_row('+',char='=')
  for idx,row in enumerate(rows):
    print_row('|',row=row)
    if inter_row_line:                                                # If we're printing inter-row lines...
      print_row('+',char='-')                                         # ... print one after each row

  if not inter_row_line:                                              # No inter-row lines?
      print_row('+',char='-')                                         # ... we still need one to wrap up the table

def show_images(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device']
  heading.extend([ p for p in settings.providers.keys() if p != 'external'])

  rows = []
  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    row = [ device ]
    for p in heading[1:]:
      p_image = settings.devices[device][p].get("image","")
      row.append(p_image)
      if p_image:
        result[device][p] = p_image

    rows.append(row)

  if args.format == 'table':
    print((args.device or "Device") + " image names by virtualization provider")
    print("")
    print_table(heading,rows)
  elif args.format in ['text','yaml']:
    print(common.get_yaml_string(result))

def show_devices(settings: Box, args: argparse.Namespace) -> None:
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
    rows.append(row)
    result[device] = dev_data.description

  if args.format == 'table':
    print('Virtual network devices supported by netlab')
    print("")
    print_table(heading,rows,inter_row_line=False)
  elif args.format in ['text','yaml']:
    print(common.get_yaml_string(result))

def show_module_support(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device']
  mod_list = sorted([ m for m in settings.keys() if 'supported_on' in settings[m]])
  heading.extend(mod_list)

  rows = []
  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    if args.format == 'table':
      row = [ device ]
      for m in heading[1:]:
        value = "x".center(len(m)) if device in settings[m].supported_on else ""
        row.append(value)
      rows.append(row)
    else:
      dev_mods = [ m for m in mod_list if device in settings[m].supported_on ]
      result[device] = dev_mods
      if args.format == 'text':
        print(f'{device}: {",".join(dev_mods)}')

  if args.format == 'table':
    print("Configuration modules supported by " + (args.device or "individual devices"))
    print("")
    print_table(heading,rows)
  elif args.format == 'yaml':
    print(common.get_yaml_string(result))

def show_modules(settings: Box, args: argparse.Namespace) -> None:
  mod_list = sorted([ m for m in settings.keys() if 'supported_on' in settings[m]])
  result = data.get_empty_box()

  if args.format == 'table':
    print("netlab Configuration modules and supported devices")
    print("=" * 75)

  for m in mod_list:
    dev_list = [ d for d in settings[m].supported_on if not d in DEVICES_TO_SKIP ]
    if args.format == 'text':
      print(f'{m}: {",".join(dev_list)}')
    elif args.format == 'table':
      print(f'{m}:')
      print(textwrap.TextWrapper(
        initial_indent="  ",
        subsequent_indent="  ").fill(", ".join(dev_list)))
    else:
      result[m] = settings[m].dev_list

  if args.format == 'yaml':
    print(common.get_yaml_string(result))

show_dispatch = {
  'images': show_images,
  'devices': show_devices,
  'module-support': show_module_support,
  'modules': show_modules
}

#
# CLI parser for 'netlab show' command
#
def show_parse(args: typing.List[str]) -> argparse.Namespace:
  global show_dispatch
  parser = argparse.ArgumentParser(
    prog='netlab show',
    description='Display default settings')
  parser.add_argument(
    '-d','--device',
    dest='device',
    action='store',
    default='*',
    help='Display information for a single device')
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
  parser.add_argument(
    dest='action',
    action='store',
    choices=show_dispatch.keys(),
    help='Select the system information to display')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  global show_dispatch
  args = show_parse(cli_args)
#  settings =  read_topology.read_yaml("package:topology-defaults.yml")
  empty_file = "package:cli/empty.yml"
  loc_defaults = empty_file if args.system else ""
  topology = read_topology.load(empty_file,loc_defaults,"package:topology-defaults.yml")
  if topology is None:
    common.fatal("Cannot read system settings")
    return

  settings = topology.defaults
  show_dispatch[args.action](settings,args)
