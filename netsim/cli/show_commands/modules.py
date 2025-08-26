#
# netlab show modules -- display supported configuration modules
#

import argparse
import textwrap
import typing

from box import Box

from ... import data
from ...utils import strings
from .. import error_and_exit
from . import DEVICES_TO_SKIP, get_modlist, parser_add_module, show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('modules','supported configuration modules')
  parser_add_module(parser)
  parser.add_argument(
    '--feature',
    dest='feature',
    action='store',
    help='Display information for a single feature of the selected module')
  return parser

def get_feature_list(features: Box,prefix: str = '') -> list:
  f_list = []
  for k in features.keys():
    if isinstance(features[k],dict):
      f_list.extend(get_feature_list(features[k],k+'.'))
    else:
      f_list.append(prefix+k)

  return f_list

def device_module_feature_row(
      settings: Box, *,
      rows: list,
      heading: list,
      device: str,
      module: str,
      provider: typing.Optional[str]) -> bool:

  d_data = settings.devices[device]
  if provider:
    features = d_data.get(f'{provider}.features',None)
    if not features or module not in features:
      return True
    features = d_data.get('features',{}) + features
  else:
    features = d_data.features

  if features is None:
    return True

  if module not in features:
    return True

  row = [ f'{device}/{provider}' if provider else device ]
  has_feature = False
  for f in heading[1:]:
    value = features[module].get(f,None)
    if value is None:
      value = ""
    elif isinstance(value,bool):
      value = "x" if value else ""
    elif isinstance(value,list):
      value = ",".join(value)
    elif isinstance(value,Box):
      value = ",".join(value.keys())
    else:
      value = str(value)

    if value:
      has_feature = True

    value = value.center(len(f))
    row.append(value)

  rows.append(row)
  return has_feature

def show_module_features(settings: Box, args: argparse.Namespace,dev_list: list) -> None:
  m = args.module
  heading = ['device']
  heading.extend(get_feature_list(settings[m].features))
  providers = settings.providers.keys()

  rows: list = []
  need_notes = False

  for d in sorted(dev_list):
    if d in DEVICES_TO_SKIP:
      continue

    if not device_module_feature_row(settings,rows=rows,heading=heading,device=d,module=m,provider=None):
      need_notes = True

    for p_name in providers:
      if not device_module_feature_row(settings,rows=rows,heading=heading,device=d,module=m,provider=p_name):
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

  if args.feature:
    if not args.module:
      error_and_exit('The --feature parameter is only valid with the --module parameter')
    if args.feature not in settings[args.module].features:
      error_and_exit(
        f'Module {args.module} does not have feature {args.feature}',
        more_hints=f'Use "netlab show defaults {args.module}.features" to display valid device features')

    # Remove all other features from the module feature list to display just the selected feature
    #
    f = settings[args.module].features[args.feature]
    settings[args.module].features = { args.feature: f }

  if args.format == 'table':
    if args.module:
      if settings[args.module].features:
        if args.feature:
          print(f"Devices supported by the {args.module} module and their support for the {args.feature} feature")
        else:
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

          # Remove all non-relevant features from device results
          #
          if args.feature:
            if args.feature in result[d]:
              result[d] = { args.feature: result[d][args.feature] }
            else:
              result[d] = {}
      else:
        result[m] = settings[m].dev_list

  if args.format == 'yaml':
    print(strings.get_yaml_string(result))
