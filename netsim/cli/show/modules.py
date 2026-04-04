#
# netlab show modules -- display supported configuration modules
#

import argparse
import textwrap
import typing

from box import Box

from ... import data
from ...utils import log, strings
from .. import error_and_exit
from .utils import DEVICES_TO_SKIP, get_modlist, parser_add_module, show_common_parser, split_table


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('modules','supported configuration modules')
  parser_add_module(parser)
  parser.add_argument(
    '--feature',
    dest='feature',
    action='store',
    help='Display information for a single feature of the selected module')
  parser.add_argument(
    '--columns',
    dest='columns',
    action='store',
    default=7,
    type=int,
    help='Maximum number of columns in the feature table(s)')
  return parser

def get_feature_list(features: dict,prefix: str = '') -> list:
  f_list = []
  for k in features.keys():
    if k == '_title':
      continue
    if isinstance(features[k],dict):
      f_list.extend(get_feature_list(features[k],k+'.'))
    else:
      f_list.append(prefix+k)

  return f_list

def get_module_flat_features(features: Box, prefix: str = '', path: str = '', f_dict: dict = {}) -> dict:
  for k,v in features.items():
    if k == '_title':
      continue
    if not isinstance(v,Box):
      f_dict[prefix+k] = {'path': path + k, 'name': v }
    elif '_title' in v:
      get_module_flat_features(v,prefix,path+k+'.',f_dict)
    else:
      get_module_flat_features(v,prefix+k+'.',path+k+'.',f_dict)

  return f_dict

def device_module_feature_row(
      settings: Box, *,
      rows: list,
      heading: list,
      device: str,
      module: str,
      provider: typing.Optional[str] = None,
      add_empty: bool = True) -> bool:

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

  if has_feature or add_empty:
    rows.append(row)
  return has_feature and add_empty

# The core "show_feature_table" processing displays a table of features
# supported by netlab platforms. The table is limited to selected features
# (feature_list), selected devices (dev_list) and potentially uses category-
# specific feature names (features).
#
# The final flag (show_notes) controls whether the "some devices support no
# extra features" text is printed. The default (true) is used for non-category
# features and the core category (category with '_title' set to none).
#
# Finally, the function splits the table into multiple tables when it has to
# display more than args.columns features and recursively calls itself to
# generate the split tables
#
def show_feature_table(
      settings: Box,
      feature_list: list,
      args: argparse.Namespace,
      dev_list: list,
      features: typing.Optional[dict] = None,
      show_notes: bool = True) -> None:
  m = args.module
  if len(feature_list) > args.columns:            # Do we need to generate multiple tables?
    for cnt,feature_cols in enumerate(split_table(feature_list,args.columns)):
      if cnt:                                     # Empty line between tables
        print()
      show_feature_table(settings,feature_cols,args,dev_list,features,show_notes)
      show_notes=False                            # Do not show notes after the first table
    return

  heading = ['device']
  heading.extend(feature_list)
  providers = settings.providers.keys()

  rows: list = []
  need_notes = False
  for d in sorted(dev_list):
    if d in DEVICES_TO_SKIP:
      continue

    if not device_module_feature_row(
              settings,rows=rows,heading=heading,device=d,module=m,provider=None,add_empty=show_notes):
      need_notes = True

    for p_name in providers:
      if not device_module_feature_row(
              settings,rows=rows,heading=heading,device=d,module=m,provider=p_name,add_empty=show_notes):
        need_notes = True

  strings.print_table(heading,rows)

  if need_notes and show_notes:
    print(f"""
Notes:
* All devices listed in the table support {m} configuration module.
* Some devices might not support any module-specific additional feature""")
    
  print("")
  print("Feature legend:")
  if not features:
    features = settings[m].features
  if not features:
    return

  for f in heading[1:]:
    print(f"* {f}: {features[f]}")

# The top-level "show features table" function splits feature categories from
# regular features, iterates over categories (printing title and showing category
# table), and finally prints regular features table.
#
# The "show notes" which displays "some devices support no features" note is set
# to True only when the category title is None (indicating "core" features
#
def show_module_features(settings: Box, args: argparse.Namespace,dev_list: list) -> None:
  m = args.module
  mod_features = settings[m].features
  categories = [ cname for cname,cdata in mod_features.items()
                    if isinstance(cdata,Box) and '_title' in cdata ]
  features = { k:v for k,v in mod_features.items() if k not in categories }

  for cname in categories:
    cdata = mod_features[cname]
    sub_category = bool(cdata.get('_title',None))
    if sub_category:
      print("\n")
      strings.print_colored_text(cdata._title,"bold")
      print("\n")

    show_feature_table(
      settings,
      feature_list=get_feature_list(cdata),
      args=args,
      dev_list=dev_list,
      features=cdata,
      show_notes=not sub_category)

  if features:
    show_feature_table(settings,get_feature_list(features),args,dev_list)

def show(settings: Box, args: argparse.Namespace) -> None:
  if args.module == 'initial':
    mod_list = [ args.module ]
  else:
    mod_list = get_modlist(settings,args)

  if args.columns < 2 or args.columns > 20:
    log.info('The value of --columns flag should be between 2 and 20. Using default value (7)')
    args.columns = 7

  result = data.get_empty_box()

  # When the user specifies the --feature flag, we have to unroll the categories features
  # into a flat list, use the flat list to check the feature value (or generate a list of
  # features) and limit the printout to the selected feature
  #
  if args.feature:
    if not args.module:
      log.fatal('The --feature flag can be used only with the --module flag')
    flat_features = get_module_flat_features(settings[args.module].features)
    if not args.module:
      error_and_exit('The --feature parameter is only valid with the --module parameter')
    if args.feature not in flat_features:
      f_list = [ f"* {k}: {flat_features[k]['name']}" for k in sorted(flat_features.keys())]
      error_and_exit(
        f'Module {args.module} does not have feature {args.feature}',
        more_hints=[f'Valid {args.module} features are:\n']+f_list)

    # Remove all other features from the module feature list to display just the selected feature
    #
    f = settings[args.module].features[flat_features[args.feature]['path']]
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
