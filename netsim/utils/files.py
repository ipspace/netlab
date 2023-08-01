#
# File handling routines
#

import pathlib
import os
import sys
import typing
import fnmatch

from . import log

try:
  from importlib import resources
  new_resources = hasattr(resources,'files')
except ImportError:
  new_resources = False
  import importlib_resources as resources         # type: ignore

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
# Find a file in a search path
#
def find_file(path: str, search_path: typing.List[str]) -> typing.Optional[str]:
  for dirname in search_path:
    candidate = os.path.join(dirname, path)
    if os.path.exists(candidate):
      return candidate

  return None

#
# Get a list of files matching a glob pattern
#
def get_globbed_files(path: typing.Any, glob: str) -> list:
  if isinstance(path,pathlib.Path):
    return [ str(fname) for fname in list(path.glob(glob)) ]
  else:
    file_names = list(path.iterdir())
    return fnmatch.filter(file_names,glob)

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
    log.fatal(f'Cannot open file {fname} for writing: {ex}')
    return sys.stdout

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
  except Exception as ex:
    log.fatal('Cannot write to {fname}: {ex}')
    return
  close_output_file(fh)
