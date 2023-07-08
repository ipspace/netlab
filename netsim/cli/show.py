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
from ..augment import main

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

def get_modlist(settings: Box, args: argparse.Namespace) -> list:
  if args.module:
    if settings[args.module].supported_on:
      return [ args.module ]
    else:
      common.fatal(f'Unknown module: {args.module}')
    
  return sorted([ m for m in settings.keys() if 'supported_on' in settings[m]])

def show_module_support(settings: Box, args: argparse.Namespace) -> None:
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

  if args.format == 'table':
    print("Configuration modules supported by " + (args.device or "individual devices"))
    print("")
    print_table(heading,rows)
  elif args.format == 'yaml':
    print(common.get_yaml_string(result))

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

      if value:
        has_feature = True

      value = value.center(len(f))
      row.append(value)
    rows.append(row)
    if not has_feature:
      need_notes = True

  print_table(heading,rows)

  if need_notes:
    print(f"""
Notes:
* All devices listed in the table support {m} configuration module.
* Some devices might not support any module-specific additional feature""")
    
  print("")
  print("Feature legend:")
  for f in heading[1:]:
    print(f"* {f}: {settings[m].features[f]}")

def show_modules(settings: Box, args: argparse.Namespace) -> None:
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
    '-m','--module',
    dest='module',
    action='store',
    help='Display information for a single module')
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

  main.topology_init(topology)
  settings = topology.defaults
  show_dispatch[args.action](settings,args)
