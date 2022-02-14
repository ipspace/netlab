#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob
from box import Box

from .. import common
from .. import read_topology

def print_table(heading: typing.List[str],rows: typing.List[typing.List[str]]) -> None:

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
    print_row('+',char='-')

def show_images(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device']
  heading.extend(settings.providers.keys())

  rows = []
  for device in settings.devices.keys():
    if device == 'none':
      continue

    if args.device and device != args.device:
      continue

    row = [ device ]
    for p in heading[1:]:
      row.append(settings.devices[device][p].get("image",""))
    rows.append(row)

  print((args.device or "Device") + " image names by virtualization provider")
  print("")
  print_table(heading,rows)

def show_module_support(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device']
  heading.extend([ m for m in settings.keys() if 'supported_on' in settings[m]])

  rows = []
  for device in sorted(settings.devices.keys()):
    if device == 'none':
      continue

    if args.device and device != args.device:
      continue

    row = [ device ]
    for m in heading[1:]:
      value = "x" if device in settings[m].supported_on else ""
      row.append(value)
    rows.append(row)

  print("Configuration modules supported by " + (args.device or "individual devices"))
  print("")
  print_table(heading,rows)

show_dispatch = {
  'images': show_images,
  'module-support': show_module_support
}

#
# CLI parser for 'netlab show' command
#
def show_parse(args: typing.List[str]) -> argparse.Namespace:
  global show_dispatch
  parser = argparse.ArgumentParser(
    prog='netlab show',
    description='Display system settings')
  parser.add_argument(
    '-d','--device',
    dest='device',
    action='store',
    help='Display system information for a single device')
  parser.add_argument(
    dest='action',
    action='store',
    choices=show_dispatch.keys(),
    help='Select the system information to display')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  global show_dispatch
  args = show_parse(cli_args)
  settings =  read_topology.read_yaml("package:topology-defaults.yml")

  if settings is None:
    common.fatal("Cannot read system settings")
  else:
    show_dispatch[args.action](settings,args)
