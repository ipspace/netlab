#
# netlab show modules -- display supported configuration modules
#

import argparse
import textwrap
from box import Box

from ...utils import strings
from ... import data
from . import show_common_parser,parser_add_module,DEVICES_TO_SKIP,get_modlist

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('modules','supported configuration modules')
  parser_add_module(parser)
  return parser

def get_feature_list(features: Box,prefix: str = '') -> list:
  f_list = []
  for k in features.keys():
    if isinstance(features[k],dict):
      f_list.extend(get_feature_list(features[k],k+'.'))
    else:
      f_list.append(prefix+k)

  return f_list

def show_module_features(settings: Box, args: argparse.Namespace,dev_list: list) -> None:
  m = args.module
  heading = ['device']
  heading.extend(get_feature_list(settings[m].features))

  rows = []
  need_notes = False

  for d in sorted(dev_list):
    if d in DEVICES_TO_SKIP:
      continue
    row = [ d ]

    has_feature = False
    for f in heading[1:]:
      value = settings.devices[d].features[m].get(f,None)
      if value is None:
        value = ""
      elif isinstance(value,bool):
        value = "x" if value else ""
      elif isinstance(value,list):
        value = ",".join(value)
      elif isinstance(value,Box):
        value = ",".join(value.keys())

      if value:
        has_feature = True

      value = value.center(len(f))
      row.append(value)
    rows.append(row)
    if not has_feature:
      need_notes = True

  strings.print_table(heading,rows)

  if need_notes:
    print(f"""
Notes:
* All devices listed in the table support {m} configuration module.
* Some devices might not support any module-specific additional feature""")
    
  print("")
  print("Feature legend:")
  for f in heading[1:]:
    print(f"* {f}: {settings[m].features[f]}")

def show(settings: Box, args: argparse.Namespace) -> None:
  if args.module == 'initial':
    mod_list = [ args.module ]
  else:
    mod_list = get_modlist(settings,args)

  result = data.get_empty_box()
  if args.format == 'table':
    if args.module:
      if settings[args.module].features:
        print(f"Devices and features supported by {args.module} module")
      else:
        print(f"Devices supported by {args.module} module")
      print("")
    else:
      print("netlab Configuration modules and supported devices")
      print("=" * 75)

  for m in mod_list:
    if m == 'initial':
      dev_list = [ d for d in settings.devices.keys() if not d in DEVICES_TO_SKIP ]
    else:
      dev_list = [ d for d in settings[m].supported_on if not d in DEVICES_TO_SKIP ]

    if args.format == 'text':
      print(f'{m}: {",".join(dev_list)}')
    elif args.format == 'table' and args.module and settings[args.module].features:
      show_module_features(settings,args,dev_list)
    elif args.format == 'table':
      print(f'{m}:')
      print(textwrap.TextWrapper(
        initial_indent="  ",
        subsequent_indent="  ").fill(", ".join(dev_list)))
    else:
      if args.module and settings[args.module].features:
        for d in dev_list:
          result[d] = settings.devices[d].features[m]
      else:
        result[m] = settings[m].dev_list

  if args.format == 'yaml':
    print(strings.get_yaml_string(result))
