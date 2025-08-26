#
# Change netlab defaults
#
import argparse
import fnmatch
import pathlib
import re
import typing

import yaml
from box import Box

from ..data import get_empty_box
from ..utils import files as _files
from ..utils import log, strings
from ..utils import read as _read
from . import error_and_exit


def defaults_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab defaults',
    description='Manage netlab default settings')
  parser.add_argument(
    '-r','--regex',
    dest='regex',
    action='store_true',
    help='Display default settings matching a regular expression')
  parser.add_argument(
    '--delete',
    dest='delete',
    action='store_true',
    help='Delete the settings matching the specified pattern from the specified datastore')
  parser.add_argument(
    '-s','--source',
    dest='source',
    action='store_true',
    help='Display the source of the default setting')
  parser.add_argument(
    '--directory',
    dest='ds_directory',
    action='store_true',
    help='Display or store settings from the current directory')
  parser.add_argument(
    '--project',
    dest='ds_project',
    action='store_true',
    help='Display or store settings from the current project defaults')
  parser.add_argument(
    '--user',
    dest='ds_user',
    action='store_true',
    help='Display or store settings from the user default file')
  parser.add_argument(
    '--system',
    dest='ds_system',
    action='store_true',
    help='Display or store settings from the system default file')
  parser.add_argument(
    '--package',
    dest='ds_package',
    action='store_true',
    help='Display settings included in netlab package')
  parser.add_argument(
    '--yes',
    dest='yes',
    action='store_true',
    help='Overwrite existing settings without a confirmation')
  parser.add_argument(
    '--yaml',
    dest='yaml',
    action='store_true',
    help='Store changed defaults in expanded YAML format')
  parser.add_argument(
    dest='setting',
    action='store',
    nargs='?',
    default='*',
    help='Specify setting to set (with s=v) or display (can be a glob)')
  return parser.parse_args(args)

'''
Build list of defaults from the supplied defaults data structure
'''
def build_defaults_list(
      defs: Box,                                  # Default data
      namespace: typing.Optional[str],            # The namespace to use when displaying data
      reobj: typing.Optional[re.Pattern],         # Pattern matching
      prefix: str = '',                           # Default prefix (used for recursive scan)
      result: typing.Optional[Box] = None) -> Box:
  
  if result is None:
    result = Box({},default_box=True)

  for k,v in defs.items():                                  # Iterate over defaults
    k_path = f'{prefix}.{k}' if prefix else k               # Get the full path to the current element
    if isinstance(v,Box):                                   # Recurse into child values
      build_defaults_list(v,namespace,reobj,k_path,result)
      continue

    if reobj is not None and reobj.search(k_path) is None:  # Are we interested in this value?
      continue

    if namespace:
      result[k_path][namespace] = v                         # Remember the value within the namespace
    else:
      result[k_path] = v                                    # No namespaces, just store the value

  return result

'''
Gather the defaults from known default sources
'''
D_SOURCES: dict = {
  'netlab': 'package:topology-defaults.yml',
  'system': '/etc/netlab/defaults.yml',
  'user (deprecated)': '~/topology-defaults.yml',
  'user': '~/.netlab.yml',
  'directory': './topology-defaults.yml',
  'project': './defaults.yml'                                   # This one is assumed and might have to changed
}

'''
Find the defaults file for the current project. It could be 'defaults.yml' in
current directory or the first element of 'defaults.sources.extra' list in
the default topology (topology.yml).

If we can't find a feasible project default file, the 'project' entry is
removed from the default sources
'''
def find_project_defaults() -> None:
  global D_SOURCES

  if pathlib.Path(D_SOURCES['project']).exists():
    return
  
  if pathlib.Path("topology.yml").exists():
    topology = _read.read_yaml("topology.yml")
    if topology:
      d_extra = topology.get('defaults.sources.extra',None)
      if d_extra and isinstance(d_extra,list):
        D_SOURCES['project'] = d_extra[0]
        return

  D_SOURCES.pop('project',None)

'''
Given candidate sources, change them into absolute paths and remove
the non-existent ones (unless we're in "write" mode)
'''
def cleanup_sources(selection: dict, write: bool = False) -> dict:
  selection = { k:v for k,v in selection.items() }              # Make a copy of the list
  for k in list(selection):
    d_file = selection[k]
    if 'package:' in d_file:                                    # Assume package files always exist
      continue
    f_path = _files.absolute_path(d_file)                       # Expand filename
    if not f_path.exists() and not write:                       # And drop it if it doesn't exist
      selection.pop(k,None)                                     # ... unless we're looking for write sources
    else:
      selection[k] = str(f_path)                                # ... otherwise store the expanded path

  return selection

def source_specified(args: argparse.Namespace) -> bool:
  return args.ds_package or args.ds_system or args.ds_user or args.ds_directory or args.ds_project

def get_sources(args: argparse.Namespace, write: bool = False) -> dict:
  global D_SOURCES

  s_list = []
  if args.ds_package and not write:
    s_list.append('netlab')
  if args.ds_system:
    s_list.append('system')
  if args.ds_user:
    s_list.append('user')
  if args.ds_directory:
    s_list.append('directory')
  if args.ds_project:
    s_list.append('project')

  if s_list:
    args.source = True
  if not s_list and write:                                      # No sources specified for a write op
    selection = { k:v for k,v in D_SOURCES.items() if k in ['user','directory','project'] }
    selection = cleanup_sources(selection)                      # Check whether we have user- or more specific src
    s_list = list(selection.keys()) or ['user']                 # Worst case, write to user defaults

  selection = { k:v for k,v in D_SOURCES.items() if k in s_list } if s_list else D_SOURCES
  selection = cleanup_sources(selection,write)

  if not selection:
    error_and_exit(f'None of the specified default sources ({",".join(s_list)}) exists on your system')

  return selection

def build_defaults_sources(reobj: typing.Optional[re.Pattern], sources: dict) -> Box:
  result = Box({},default_box=True)
  for ns,d_file in sources.items():
    defaults = _read.read_yaml(d_file)
    if defaults:
      result = build_defaults_list(defaults,namespace=ns,reobj=reobj,result=result)

  return result

'''
Create compiled regex from input prefix, glob, or regex
'''
def get_re_pattern(txt: str, regex: bool = False) -> re.Pattern:
  try:
    if not regex:                                           # Input parameter is not a regex match
      if any([k in txt for k in ['*','[']]):                # ... is it a glob?
        txt = fnmatch.translate(txt)                        # ... next, translate glob to regex
        txt = "\\A" + txt
      else:
        txt = "\\A" + txt.replace('.','[.]') + "(\\.|\\Z)"  # ... nope, it's a prefix, make a regex out of it
    reobj = re.compile(txt)                                 # ... and compile the regex
  except Exception as ex:
    error_and_exit(f'Cannot parse {"regex" if regex else "glob pattern"} {txt}',more_hints=str(ex))
  
  return reobj

def print_def_list(def_expanded: Box, show_source: bool) -> None:
  for k in sorted(def_expanded):
    ns_list = list(def_expanded[k])
    if show_source:
      for ns in ns_list:
        txt = f'{k} = {def_expanded[k][ns]} ({ns})'
        if ns != ns_list[-1] and strings.rich_color:
          strings.rich_console.print(f'[dim]{txt}[/dim]')
        else:
          print(txt)
    else:
      print(f'{k} = {def_expanded[k][ns_list[-1]]}')

def default_show(args: argparse.Namespace) -> None:
  global D_SOURCES
  reobj = get_re_pattern(args.setting,args.regex)

  d_sources = get_sources(args)
  def_expanded = build_defaults_sources(reobj,d_sources)
  
  if def_expanded:
    print_def_list(def_expanded,args.source)
  else:
    d_src_txt = '' if d_sources == D_SOURCES else f' in {",".join(d_sources)} defaults'
    error_and_exit(f'{args.setting}{" regular expression" if args.regex else ""} not found{d_src_txt}',module='-')

"""
Read comments from a defaults file. Return two lists of comment lines, one at the top of the file,
the other containing all other comments.
"""
def read_comments(src: str) -> typing.List[list]:
  d_path = pathlib.Path(src)
  c_list: typing.List[list] = [[],[]]
  if not d_path.exists():
    return c_list

  lines = d_path.read_text().split('\n')
  c_cnt = 0
  for line in lines:
    if line.strip().startswith('#'):
      c_list[c_cnt].append(line)
    elif not c_cnt:
      c_cnt = 1

  return c_list

"""
Expand settings into the 'path: value' format
"""
def path_value_settings(data: Box) -> str:
  list_data = build_defaults_list(data,None,None)
  return list_data.to_yaml()

"""
Update defaults datastore
"""
def update_datastore(data: Box, path: str, store_as_yaml: bool) -> None:
  d_comments = read_comments(path)
  d_comments[0].append('---')
  if store_as_yaml:
    contents = data.to_yaml()
  else:
    contents = path_value_settings(data)

  txt = "\n".join(["\n".join(d_comments[0]),contents,"\n".join(d_comments[1])]) + "\n"
  pathlib.Path(path).write_text(txt)

"""
Make the change to the specified setting
"""
def change_default_setting(s_path: str, s_value: typing.Any, src: str, store_as_yaml: bool) -> None:
  try:
    d_data = _read.read_yaml(src)
    if d_data is None:
      d_data = get_empty_box()

    d_data[s_path] = s_value
    update_datastore(d_data,src,store_as_yaml)
    print(f"{s_path} set to {s_value} in {src}")
  except Exception as ex:
    error_and_exit(
      f'Cannot set {s_path} to {s_value} in {src}',
      more_hints=str(ex))

"""
Change a default setting
"""
def default_set(args: argparse.Namespace) -> None:
  global D_SOURCES

  s_params = args.setting.split('=')
  if len(s_params) != 2:
    error_and_exit('To set a default paramenter, use path=value syntax')
  s_path = s_params[0].strip()
  try:
    s_value = yaml.load(s_params[1].strip(),Loader=yaml.SafeLoader)
  except Exception as ex:
    error_and_exit(f'Cannot parse the specified value {s_params[1]}',more_hints=str(ex))

  w_sources = get_sources(args,write=True)
  w_best_src = list(w_sources)[-1]
  all_data = build_defaults_sources(None,cleanup_sources(D_SOURCES,False))
  more_specific = [ src for k in all_data.keys() if k.startswith(s_path+".") for src in all_data[k] ]
  if more_specific:
    if isinstance(all_data[s_path],Box):
      ms_set = set(more_specific)
      error_and_exit(
        f'Cannot change a default setting \'{s_path}\' that has more-specific values in {",".join(ms_set)} defaults',
        more_hints=[
          f'Use "netlab defaults {s_path}" to display the more-specific values'])
  if s_path in all_data:
    if not args.yes:
      print(f'The default setting {s_path} is already set in {",".join(all_data[s_path])} defaults')
      if not strings.confirm(f"Do you want to change that setting in {w_best_src} defaults"):
        return

  change_default_setting(s_path,s_value,w_sources[w_best_src],args.yaml)

'''
Delete specified settings
'''
def default_delete(args: argparse.Namespace) -> None:
  if not source_specified(args):
    error_and_exit('You have to specify the datastore from which you want to delete the settings')

  d_sources = get_sources(args)
  if len(d_sources) > 1:
    error_and_exit('You can specify only a single datastore for the delete operation')
  if 'netlab' in d_sources:
    error_and_exit('You can delete settings from the built-in defaults')

  reobj = get_re_pattern(args.setting,args.regex)
  def_expanded = build_defaults_sources(reobj,d_sources)
  if not def_expanded:
    error_and_exit(f'No settings match the specified pattern {args.setting}')

  ds_name = list(d_sources)[0]
  print(f"The following settings will be deleted from the {ds_name} defaults:\n")
  for k,v in def_expanded.items():
    print(f'{k}: {list(v.values())[0]}')

  if not args.yes and not strings.confirm('\nDo you want to delete these settings'):
    return

  df_name = d_sources[ds_name]
  d_data = _read.read_yaml(df_name)
  if d_data is None:
    error_and_exit(f'Cannot read defaults from {df_name}')
  if args.yaml:
    for k in def_expanded.keys():
      d_data.pop(k,None)
    update_datastore(d_data,df_name,args.yaml)
  else:
    list_data = Box({ k:v for k,v in build_defaults_list(d_data,None,None).items() if k not in def_expanded })
    update_datastore(list_data,df_name,args.yaml)

  print(f"The specified settings were deleted from {df_name}")

def run(cli_args: typing.List[str]) -> None:
  args = defaults_parse(cli_args)
  log.set_logging_flags(args)
  if args.setting.startswith('default'):
    error_and_exit("Remove the 'defaults' prefix, we know you're changing the defaults")
  find_project_defaults()
  if args.delete:
    default_delete(args)
  elif '=' in args.setting:
    default_set(args)
  else:
    default_show(args)
