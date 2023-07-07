#
# File handling routines
#

import pathlib
import os
import typing

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
# Get the usual search path
#

def get_search_path(path_component: typing.Optional[str] = None) -> list:
  path = [ get_curdir(),get_userdir(),get_sysdir(),get_moddir() ]
  if path_component:
    path = [ pc / path_component for pc in path ]
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

