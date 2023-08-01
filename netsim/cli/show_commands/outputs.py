#
# netlab show outputs command -- display output modules
#

import argparse
import os
from box import Box

from ...utils import strings,log,files as _files
from ... import data
from ...outputs import _TopologyOutput
from . import show_common_parser

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('outputs','output modules for the "netlab create" command',system_only=False)
  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  heading = ['module','description']

  rows = []
  result = data.get_empty_box()
  modpath = _files.get_traversable_path('package:outputs')  # Get output modules directory as traversable path
  modlist = _files.get_globbed_files(modpath,'*.py')        # ... and find all Python files in that directory

  for mname in sorted(modlist):                             # Iterate over Python files in 'outputs' directory
    mname = os.path.basename(mname).split('.')[0]           # Get just the name of the output module
    if '_' in mname:                                        # ... and skip internal files
      continue

    module = _TopologyOutput.load(mname,Box({}))            # Load the module
    if not module:                                          # ... and skip files without a usable class
      continue

    mdesc = getattr(module,'DESCRIPTION','')                # Try to get class description
    if not mdesc:                                           # ... skip objects without a usable description
      continue

    row = [ mname,mdesc ]
    rows.append(row)
    result[mname] = mdesc

  if args.format == 'table':
    print('Supported output modules')
    print("")
    strings.print_table(heading,rows,inter_row_line=False)
  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
