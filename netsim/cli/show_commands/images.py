#
# netlab show images command -- display default images
#

import argparse
from box import Box

from ...utils import strings
from ... import data
from . import show_common_parser,parser_add_device,DEVICES_TO_SKIP

def parse() -> argparse.ArgumentParser:

  parser = show_common_parser('images','default device images')
  parser_add_device(parser)
  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
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
    if args.device == '*' or not args.device:
      args.device = "Device"

    print(f"{args.device} image names by virtualization provider")
    print("")
    strings.print_table(heading,rows)
  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
