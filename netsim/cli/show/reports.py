#
# netlab show reports command -- display available reports
#

import argparse
import os
import typing

from box import Box

from ... import data
from ...utils import files as _files
from ...utils import strings
from . import show_common_parser


def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('reports','available system reports',system_only=False)
  parser.add_argument(
    nargs='?',
    dest='match',
    action='store',
    help='Display report names containing the specified string')

  return parser

#
# Get report description: it should be in a JInja2 comment starting with 'description:'
#

d_marker :str = '{# description:'                           # Report description marker -- has to be in a report

def get_description(fname: str) -> typing.Optional[str]:
  global d_marker
  try:
    with open(fname,'r') as r_file:                         # Try to read the report file
      r_text = r_file.read()
      r_file.close()
  except:                                                   # No description if we can't read it for whatever reason
    return None

  dsc_idx = r_text.find(d_marker)                           # Try to find description marker
  if dsc_idx < 0:                                           # ... and skip the file if it's missing
    return None

  r_text = r_text[dsc_idx + len(d_marker):]                 # Skip text before the description marker
  dsc_end = r_text.find('#}')                               # Try to find the end of the description
  if dsc_end < 5:                                           # Description has to have some realistic length
    return None
  
  return r_text[:dsc_end].strip()

type_heading :dict = {
  'html': 'HTML reports',
  'text': 'text reports',
  'md'  : 'Markdown reports',
}

def print_subset_table(result: Box) -> None:
  heading = ['format','report','description']
  rows = []
  last_type = ''

  for r_type in result.keys():                              # Iterate over collected report types
    for n,d in result[r_type].items():                      # Build results table from results dictionary
      row_type = '' if last_type == r_type else r_type      # Display report format only when it changes
      last_type = r_type
      rows.append([ row_type,d.name,d.desc ])

  strings.print_table(heading,rows,inter_row_line=False)    # Print the results

def print_result_table(result: Box) -> None:
  global type_heading
  heading = ['report','description']

  for r_type in type_heading.keys():                        # Iterate over known report types
    if not r_type in result:                                # Skip types that have no relevant report
      continue
  
    print("")
    print(type_heading[r_type])                             # Print section header
    print("")
    rows = []
    for n,d in result[r_type].items():                      # Build results table from results dictionary
      rows.append([ d.name,d.desc ])

    strings.print_table(heading,rows,inter_row_line=False)  # and print it

def show(settings: Box, args: argparse.Namespace) -> None:
  result = data.get_empty_box()
  r_path = _files.get_traversable_path('package:reports')   # Get reports directory as traversable path
  r_list = _files.get_globbed_files(r_path,'*.j2')          # ... and find all Jinja2 files in that directory

  for r_name in sorted(r_list):                             # Iterate over report templates
    if '.include' in r_name:                                # Skip include files
      continue

    if args.match and not args.match in r_name:             # Skip reports not matching the name filter
      continue

    r_desc = get_description(r_name)                        # Get report description
    if r_desc is None:                                      # ... skip the file if it has no usable description
      continue

    # Get report type
    r_type = 'html' if '.html.j2' in r_name else 'md' if '.md.j2' in r_name else 'text'      
    r_id = os.path.basename(r_name).split('.')[0]           # report ID: file name up to the first dot
    r_name = os.path.basename(r_name).replace('.j2','')     # report name: file name without .j2

    result[r_type][r_id] = {
      'name': r_name,
      'desc': r_desc }                                      # Save the results

  if args.format == 'table':
    if args.match:
      print_subset_table(result)
    else:
      print_result_table(result)
  elif args.format in ['text','yaml']:
    print(strings.get_yaml_string(result))
