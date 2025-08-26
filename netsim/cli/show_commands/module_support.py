#
# netlab show module-support command -- display configuration module support per device
#

import argparse
import math

from box import Box

from ... import data
from ...utils import strings
from . import DEVICES_TO_SKIP, get_modlist, parser_add_device, parser_add_module, show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('module-support','configuration modules supported by individual devices')
  parser_add_device(parser)
  parser_add_module(parser)
  return parser

def print_table(result: Box, args: argparse.Namespace, mod_list: list) -> None:
  if args.device == '*' or not args.device:
    args.device = 'individual devices'

  if args.module:
    print(f'{args.module} configuration module support')
  else:
    print(f"Configuration modules supported by {args.device}")

  columns = min(max(int(strings.rich_width/10),5),10)
  for t_cnt in range(math.ceil(len(mod_list)/columns)):
    rows = []
    heading = ['device']
    heading.extend(mod_list[t_cnt * columns:][:columns])
    for device,d_support in result.items():
      row = [ device ]
      for m in heading[1:]:
        value = "x".center(len(m)) if m in d_support else ""
        row.append(value)
      rows.append(row)

    print("")
    strings.print_table(heading,rows)

def collect_device_module_data(settings: Box, args: argparse.Namespace) -> Box:
  mod_list = get_modlist(settings,args)
  provider_list = settings.providers.keys()

  result = data.get_empty_box()
  for device in sorted(settings.devices.keys()):
    if device in DEVICES_TO_SKIP:
      continue

    if device != args.device and args.device != '*':
      continue

    dev_mods = [ m for m in mod_list if device in settings[m].supported_on ]
    for m in dev_mods:
      f_value = settings.devices[device].features.get(m,True)
      if f_value is None or (not f_value and isinstance(f_value,dict)):
        f_value = True
      for p_name in provider_list:
        p_features = settings.devices[device].get(f'{p_name}.features.{m}')
        if not p_features:
          continue
        p_features.pop('_provider',None)
        if f_value is True:
          f_value = data.get_box({p_name: p_features})
        else:
          f_value[p_name] = p_features

      result[device][m] = f_value
  
  return result

def show(settings: Box, args: argparse.Namespace) -> None:
  result = collect_device_module_data(settings,args)

  if args.format == 'table':
    print_table(result,args,get_modlist(settings,args))
  elif args.format == 'text':
    for device,dev_mods in result.items():
      print(f'{device}: {",".join(dev_mods)}')
  else:
    print(strings.get_yaml_string(result))
