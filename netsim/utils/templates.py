#
# Common routines for create-topology script
#
import sys
import typing
import os
import pathlib

from jinja2 import Environment, PackageLoader, FileSystemLoader, StrictUndefined, make_logging_undefined
from box import Box,BoxList

from .log import debug_active

#
# Find path to the module directory (needed for various templates)
#
def get_moddir() -> pathlib.Path:
  return pathlib.Path(__file__).resolve().parent.parent

#
# Find a file in a search path
#
def find_file(path: str, search_path: typing.List[str]) -> typing.Optional[str]:
  for dirname in search_path:
    candidate = os.path.join(dirname, path)
    if os.path.exists(candidate):
      return candidate

  return None

def template(j2: str , data: typing.Dict, path: str, user_template_path: typing.Optional[str] = None) -> str:
  if path [0] in ('.','/'):                             # Absolute path or path relative to current directory?
    template_path = [ path ]
  else:                                                 # Path relative to netsim module, add module path to it
    template_path = [ str(get_moddir() / path) ]
  if not user_template_path is None:
    template_path = [ './' + user_template_path, os.path.expanduser('~/.netlab/'+user_template_path) ] + template_path
  if debug_active('template'):
    print(f"TEMPLATE PATH for {j2}: {template_path}")
  ENV = Environment(loader=FileSystemLoader(template_path), \
          trim_blocks=True,lstrip_blocks=True, \
          undefined=make_logging_undefined(base=StrictUndefined))
  template = ENV.get_template(j2)
  return template.render(**data)

#
# write_template: Applies a custom template (in_folder/j2) and writes it to the given file path (out_folder/filename)
#
def write_template(in_folder: str, j2: str, data: typing.Dict, out_folder: str, filename: str) -> None:
  if debug_active('template'):
    print(f"write_template {in_folder}/{j2} -> {out_folder}/{filename}")
  pathlib.Path(out_folder).mkdir(parents=True, exist_ok=True)
  out_file = f"{out_folder}/{filename}"
  with open(out_file,mode='w') as output:
    output.write(template(j2,data,in_folder))
