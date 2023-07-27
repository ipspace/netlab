#
# File handling routines
#

import pathlib
import os
import sys
import typing
from . import log

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
