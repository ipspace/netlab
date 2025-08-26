#
# netlab show images command -- display default images
#

import argparse

from box import Box

from ... import data
from ...utils import strings
from .. import error_and_exit
from . import DEVICES_TO_SKIP, parser_add_device, parser_add_provider, show_common_parser


def parse() -> argparse.ArgumentParser:

  parser = show_common_parser('images','default device images')
  parser_add_device(parser)
  parser_add_provider(parser)
  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  if args.provider and args.provider not in settings.providers:
    error_and_exit(f'Invalid provider {args.provider}. Use "netlab show providers" to display valid providers')

  heading = ['device']
  if args.provider:
    heading.append(args.provider)
  else:
    heading.extend([ p for p in settings.providers.keys() if p != 'external'])

  rows = []
  caveats = []
  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    row = [ device ]
    has_image = False
    for p in heading[1:]:
      p_data = settings.devices[device][p]
      p_image = p_data.get("image","")
      if p_image:
        result[device][p] = p_image
        if p_data.caveats:
          data.append_to_list(result[device],'caveats',p_data.caveats,flatten=True)
          caveats.extend(p_data.caveats if isinstance(p_data.caveats,list) else [ p_data.caveats ])
          p_image = '❗' + p_image
        has_image = True

      row.append(p_image)

    if has_image:
      rows.append(row)

  if args.format == 'table':
    if args.device == '*' or not args.device:
      args.device = "Device"

    p_text = f'for provider {args.provider}' if args.provider else 'by virtualization provider'
    print(f"{args.device} image names {p_text}")
    print("")
    strings.print_table(heading,rows,inter_row_line=False)
    if caveats:
      strings.print_colored_text('\nCaveats:\n\n',color='bold')
      for cv in caveats:
        print(strings.wrap_error_message(f'* {cv}',indent=2))

  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
