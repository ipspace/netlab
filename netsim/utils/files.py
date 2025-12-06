#
# File handling routines
#

import importlib
import importlib.util
import os
import pathlib
import sys
import textwrap
import typing

from ..data import global_vars
from . import log

try:
  from importlib import resources
  new_resources = hasattr(resources,'files')
except ImportError:
  new_resources = False
  import importlib_resources as resources  # type: ignore

#
# Find paths to module, user and system directory (needed for various templates)
#
def get_moddir() -> pathlib.Path:
  return pathlib.Path(__file__).resolve().parent.parent

def get_userdir() -> pathlib.Path:
  return pathlib.Path(os.path.expanduser("~/.netlab")).resolve()

def get_sysdir() -> pathlib.Path:
  return pathlib.Path("/etc/netlab").resolve()

def get_curdir() -> pathlib.Path:
  return pathlib.Path(os.path.expanduser(".")).resolve()

#
# Get the usual search path (current directory, user home directory, system-wide settings, package settings)
#
# If needer, augment the search path componentswith a subdirectory path. User/system subdirectory could
# be different from package subdirectory
#

def get_search_path(
      path_component: typing.Optional[str] = None,
      pkg_path_component: typing.Optional[str] = None) -> list:
  path = [ get_curdir(),get_userdir(),get_sysdir() ]
  if path_component:
    path = [ pc / path_component for pc in path ]
    pkg_path_component = pkg_path_component or path_component

  path.append(get_moddir() / pkg_path_component if pkg_path_component else get_moddir())

  return [ str(pc) for pc in path ]

#
# Get absolute path to a file (handling paths relative to other files and home directories)
#

def absolute_path(fname: str, base: typing.Optional[str] = None) -> pathlib.Path:
  if fname.find('~') == 0:                                  # Resolve home directory into an absolute path
    fname = os.path.expanduser(fname)

  if os.path.isabs(fname):                                  # If we're dealing with an absolute path
    return pathlib.Path(fname).resolve()                    # ... return the fully-resolved path
  
  if base is not None:                                      # Do we need path relative to another file?
    if not os.path.isdir(base):                             # ... or directory?
      base = os.path.dirname(base)

    return (pathlib.Path(base) / fname).resolve()           # Return fully-resolved relative path starting from base directory
  else:
    return pathlib.Path(fname).resolve()                    # Return fully-resolved path

"""
Transform a search path into an absolute search path

* replace 'package:' with get_moddir()
* add topology directory to any other path
"""
def expand_package(path: str) -> pathlib.Path:
  return get_moddir () / path.replace('package:','')

def absolute_search_path(
      path: typing.List[str],
      curdir: str = '.',
      skip_missing: bool = False) -> typing.List[str]:
  a_path = []
  for p_entry in path:
    if 'package:' in p_entry:
      p_abs = expand_package(p_entry)
    elif 'topology:' in p_entry:
      topology = global_vars.get_topology()
      if topology:
        topo_name = topology.input[0]
        if topo_name.startswith('package:'):
          p_abs = expand_package(os.path.dirname(topo_name))
        else:
          topo_dir = os.path.dirname(topo_name)+"/"
          p_abs = pathlib.Path(p_entry.replace('topology:',topo_dir))
      else:
        continue
    elif p_entry.find('~') == 0:
      p_abs = pathlib.Path(os.path.expanduser(p_entry))
    elif p_entry[0] in ['.','/']:
      p_abs = pathlib.Path(p_entry)    
    else:
      p_abs = pathlib.Path(curdir) / p_entry

    p_final = str(p_abs.resolve())
    if not p_final in a_path:
      if p_abs.is_dir() or not skip_missing:
        a_path.append(p_final)

  return a_path

# 
# Find a file in a search path
#
def find_file(path: str, search_path: typing.List[str]) -> typing.Optional[str]:
  for dirname in search_path:
    candidate = os.path.join(dirname, path)
    if os.path.exists(candidate):
      if log.debug_active('paths'):
        log.info(f'Searching for {path} in:',more_data=textwrap.indent('\n'.join(search_path),'  - '))
        log.info(f'Found {candidate}')
      return candidate

  if log.debug_active('paths'):
    log.info(f'Failed to find {path} in:',more_data=textwrap.indent('\n'.join(search_path),'  - '))

  return None

#
# Get a list of files matching a glob pattern
#
def get_globbed_files(path: typing.Any, glob: str) -> list:
  if isinstance(path,str):
    path = pathlib.Path(path)
  if isinstance(path,pathlib.Path):
    return [ str(fname) for fname in list(path.glob(glob)) ]
  else:
    log.fatal(f'Internal error: invalid argument to get_globbed_files: {path}')

#
# Get a path object that can be used to find files in a file system or in the package
#

def get_traversable_path(dir_name : str) -> typing.Any:
  if 'package:' in dir_name:
    dir_name = dir_name.replace('package:','')
    pkg_files: typing.Any = None

    if not new_resources:
      pkg_files = pathlib.Path(get_moddir())
    else:
      package = '.'.join(__name__.split('.')[:-2])
      pkg_files = resources.files(package)        # type: ignore
    if dir_name == '':
      return pkg_files
    else:
      return pkg_files.joinpath(dir_name)
  else:
    return pathlib.Path(dir_name)

#
# Open, close, and write to file (or STDOUT)
#

def open_output_file(fname: str) -> typing.TextIO:
  if fname == '-':
    return sys.stdout

  try:
    return open(fname,mode='w')
  except Exception as ex:
    log.fatal(f'Cannot open file {fname} for writing: {str(ex)}')

def close_output_file(f: typing.TextIO) -> None:
  try:
    if f.name != '<stdout>':
      f.close()
  except Exception as ex:
    log.fatal(f'Cannot close file {f.name}: {ex}')

def create_file_from_text(fname: str, txt: str) -> None:
  fh = open_output_file(fname)
  try:
    fh.write(txt)
  except Exception:
    log.fatal('Cannot write to {fname}: {ex}')
    return
  close_output_file(fh)

def load_python_module(module_name: str, module_path: str) -> typing.Any:
  try:
    modspec  = importlib.util.spec_from_file_location(module_name,module_path)
    assert(modspec is not None)
    pymodule = importlib.util.module_from_spec(modspec)
    sys.modules[module_name] = pymodule
    assert(modspec.loader is not None)
    modspec.loader.exec_module(pymodule)
  except:
    log.error(
      text=f'Failed to load plugin {module_name} from {module_path}',
      category=log.IncorrectType,
      more_hints=[ 'Error reported by module loader:', str(sys.exc_info()[1]) ],
      module='loader')
    return None

  return pymodule
