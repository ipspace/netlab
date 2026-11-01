#
# netlab show plugins command -- display plugins available on the plugin search path
#
# The plugin information is extracted from the plugin source code (we don't want
# to execute the plugin code just to display its description). The default plugins
# (defaults.plugin) are still loaded by the 'netlab show' setup code, as they might
# modify the plugin search path.
#

import argparse
import ast
import pathlib
import typing

from box import Box

from ... import data
from ...utils import files as _files
from ...utils import log, strings
from ...utils import read as _read
from .utils import show_common_parser

PLUGIN_METADATA = [ '_description', '_requires', '_execute_after', '_config_name', '_redirect' ]
PLUGIN_HOOKS = [
  'topology_expand', 'init', 'pre_transform', 'pre_node_transform', 'post_node_transform',
  'pre_link_transform', 'post_link_transform', 'post_transform', 'pre_quirks', 'post_quirks',
  'post_provider_transform', 'cleanup', 'output', 'post_output' ]
SHELL_HOOK_PREFIXES = ( 'pre_shell_', 'post_shell_' )

def parse() -> argparse.ArgumentParser:
  parser = show_common_parser('plugins','plugins available on the plugin search path')
  parser.add_argument(
    '-p','--plugin',
    dest='p_name',                                          # 'plugin' would add the plugin to the dummy topology
    metavar='PLUGIN',
    action='store',
    help='Display information for a single plugin')
  parser.add_argument(
    nargs='?',
    default='',
    dest='match',
    action='store',
    help='Display plugins with names containing the specified string')

  return parser

'''
Extract plugin metadata (description, dependencies...) and hooks from the plugin source code
'''
def read_plugin_source(p_file: pathlib.Path) -> Box:
  result = data.get_empty_box()
  try:
    tree = ast.parse(p_file.read_text())
  except Exception as ex:
    result.error = f'Cannot parse {p_file}: {str(ex)}'
    return result

  hooks = []
  for stmt in tree.body:
    if isinstance(stmt,ast.FunctionDef):                    # Collect plugin hooks
      if stmt.name in PLUGIN_HOOKS or stmt.name.startswith(SHELL_HOOK_PREFIXES):
        hooks.append(stmt.name)
      continue

    if isinstance(stmt,ast.Assign) and len(stmt.targets) == 1:
      target, value = stmt.targets[0], stmt.value
    elif isinstance(stmt,ast.AnnAssign) and stmt.value is not None:
      target, value = stmt.target, stmt.value
    else:
      continue

    if not isinstance(target,ast.Name) or target.id not in PLUGIN_METADATA:
      continue
    try:                                                    # Metadata should be simple literals
      result[target.id[1:]] = ast.literal_eval(value)       # ... skip anything more convoluted
    except Exception:
      pass

  if hooks:
    result.hooks = hooks
  return result

'''
Add the information found in the plugin directory: configuration templates and plugin defaults
'''
def read_plugin_directory(p_dir: pathlib.Path, p_info: Box) -> None:
  templates = sorted([ t.stem for t in p_dir.glob('*.j2') if not t.name.startswith('_') ])
  if templates:
    p_info.templates = templates

  defaults_file = p_dir / 'defaults.yml'
  if not defaults_file.exists():
    return

  p_info.defaults = str(defaults_file)
  try:
    p_defaults = _read.read_yaml(str(defaults_file))
  except Exception:
    return
  if isinstance(p_defaults,Box) and isinstance(p_defaults.get('devices',None),Box):
    p_info.devices = sorted(p_defaults.devices.keys())

'''
Build plugin information for a plugin found in a plugin source file
'''
def get_plugin_info(p_name: str, p_file: pathlib.Path, source: str) -> Box:
  p_info = read_plugin_source(p_file)
  p_info.name = p_name
  p_info.source = source
  p_info.file = str(p_file)
  if p_file.name in ('__init__.py','plugin.py'):            # Directory-based plugins can have templates and defaults
    read_plugin_directory(p_file.parent,p_info)
  return p_info

'''
Find plugins in a search path directory. A plugin is either a Python file or a
subdirectory containing __init__.py or plugin.py file (see augment.plugin.load_plugin_from_path)
'''
def find_path_plugins(p_dir: pathlib.Path) -> typing.Generator:
  for entry in sorted(p_dir.iterdir()):
    if entry.name.startswith(('_','.')):
      continue
    if entry.is_file() and entry.suffix == '.py':
      yield (entry.stem,entry)
    elif entry.is_dir():
      for fn in ('__init__.py','plugin.py'):
        if (entry / fn).exists():
          yield (entry.name,entry / fn)
          break

'''
Find netlab built-in plugins (netsim.extra modules). Plugin names are dotted module paths
'''
def find_package_plugins(p_dir: pathlib.Path) -> typing.Generator:
  for p_file in sorted(p_dir.rglob('__init__.py')):
    rel_path = p_file.parent.relative_to(p_dir)
    if any(part.startswith(('_','.')) for part in rel_path.parts):
      continue
    yield ('.'.join(rel_path.parts),p_file)

'''
Display a search path directory in a user-friendly format
'''
def source_name(p_dir: pathlib.Path) -> str:
  cwd = pathlib.Path.cwd()
  home = pathlib.Path.home()
  if p_dir == cwd:
    return '.'
  if p_dir.is_relative_to(home):
    return '~/' + str(p_dir.relative_to(home))
  return str(p_dir)

'''
Display a file path in a user-friendly format
'''
def display_path(path: str) -> str:
  p_file = pathlib.Path(path)
  moddir = _files.get_moddir()
  if p_file.is_relative_to(moddir):
    return 'package:' + str(p_file.relative_to(moddir))
  for base,prefix in ((pathlib.Path.cwd(),'./'),(pathlib.Path.home(),'~/')):
    if p_file.is_relative_to(base):
      return prefix + str(p_file.relative_to(base))
  return path

'''
Collect all plugins on the plugin search path (or just the plugin with the specified name).
The first plugin with a given name wins (that's the one netlab would load), the built-in
plugins are loaded last.

Plugin names contain dots, so we have to use a regular dictionary instead of a Box
'''
def get_plugins(settings: Box, select: typing.Optional[str] = None) -> dict:
  plugins: dict = {}
  moddir = _files.get_moddir()

  for path in settings.paths.plugin:
    p_dir = pathlib.Path(path)
    if not p_dir.is_dir() or p_dir.is_relative_to(moddir):  # Skip missing directories and netlab package directories
      continue
    for p_name,p_file in find_path_plugins(p_dir):
      if p_name in plugins or (select and p_name != select):
        continue
      plugins[p_name] = get_plugin_info(p_name,p_file,source_name(p_dir))
      if select:                                            # Found the plugin we were looking for
        return plugins

  for p_name,p_file in find_package_plugins(moddir / 'extra'):
    if p_name in plugins or (select and p_name != select):
      continue
    plugins[p_name] = get_plugin_info(p_name,p_file,'netlab')

  return plugins

def as_text(value: typing.Any) -> str:
  return ', '.join(value) if isinstance(value,list) else str(value)

'''
Display a single plugin as a two-column (property/value) table
'''
def show_single_plugin(plugins: dict, args: argparse.Namespace) -> None:
  if args.p_name not in plugins:
    log.fatal(f'Unknown plugin {args.p_name}, use "netlab show plugins" to list available plugins')

  p_info = plugins[args.p_name]
  if args.format == 'yaml':
    print(strings.get_yaml_string({ args.p_name: p_info }))
    return

  labels = {
    'name': 'plugin',
    'description': 'description',
    'source': 'source',
    'file': 'file',
    'redirect': 'replaced by',
    'requires': 'requires',
    'execute_after': 'executes after',
    'config_name': 'config template',
    'hooks': 'hooks',
    'templates': 'device templates',
    'devices': 'device settings',
    'defaults': 'defaults',
    'error': 'error' }
  rows = [
    [ label,display_path(p_info[key]) if key in ('file','defaults') else as_text(p_info[key]) ]
      for key,label in labels.items() if p_info.get(key,None) ]

  if args.format == 'table':
    strings.print_table(['property','value'],rows,inter_row_line=False)
  else:
    for label,value in rows:
      print(f'{label}: {value}')

  if p_info.defaults and args.format == 'table':          # Don't mess up the parseable text format
    print("")
    print(f'Use "netlab show attributes --plugin {args.p_name}" to display the attributes defined by the plugin')

'''
Display a summary of all plugins with a description (other plugins are considered internal)
'''
def show_plugin_summary(plugins: dict, args: argparse.Namespace) -> None:
  heading = ['plugin','description','requires','source']
  rows = []
  result: dict = {}
  for p_name in sorted(plugins.keys()):
    p_info = plugins[p_name]
    if not p_info.description:                              # Skip internal plugins
      continue
    if args.match and args.match not in p_name:             # ... and plugins not matching the name filter
      continue

    rows.append([ p_name,p_info.description,as_text(p_info.requires or []),p_info.source ])
    result[p_name] = data.get_box({ 'description': p_info.description, 'source': p_info.source })
    if p_info.requires:
      result[p_name].requires = p_info.requires

  if args.format == 'table':
    if not args.match:
      print('Plugins available on the plugin search path')
      print("")
    strings.print_table(heading,rows,inter_row_line=False)
  elif args.format == 'text':
    for p_name,p_data in result.items():
      requires = f"; requires: {as_text(p_data.requires)}" if p_data.requires else ""
      print(f"{p_name} ({p_data.description}): {p_data.source}{requires}")
  else:
    print(strings.get_yaml_string(result))

def show(settings: Box, args: argparse.Namespace) -> None:
  plugins = get_plugins(settings,args.p_name)
  if args.p_name:
    show_single_plugin(plugins,args)
  else:
    show_plugin_summary(plugins,args)
