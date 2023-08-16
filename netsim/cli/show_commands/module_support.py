#
# netlab show module-support command -- display configuration module support per device
#

import argparse
import textwrap
from box import Box

from ...utils import strings
from ... import data
from . import show_common_parser,parser_add_module,parser_add_device,DEVICES_TO_SKIP,get_modlist

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('module-support','configuration modules supported by individual devices')
  parser_add_device(parser)
  parser_add_module(parser)
  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  heading = ['device']
  mod_list = get_modlist(settings,args)
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
      if args.device and args.format == 'yaml':
        for m in dev_mods:
          f_value = settings.devices[device].features.get(m,True)
          if f_value is None or (not f_value and isinstance(f_value,dict)):
            f_value = True
          result[m] = f_value
      else:
        result[device] = dev_mods
      if args.format == 'text':
        print(f'{device}: {",".join(dev_mods)}')

  if args.device == '*' or not args.device:
    args.device = 'individual devices'

  if args.format == 'table':
    if args.module:
      print(f'{args.module} configuration module support')
    else:
      print(f"Configuration modules supported by {args.device}")
    print("")
    strings.print_table(heading,rows)
  elif args.format == 'yaml':
    print(strings.get_yaml_string(result))
