#
# Common routines for create-topology script
#
import functools
import pathlib
import typing

from jinja2 import Environment, FileSystemLoader, StrictUndefined, make_logging_undefined

from . import filters
from .files import create_file_from_text, get_moddir
from .log import debug_active, fatal


def add_j2_filters(ENV: Environment) -> None:
  for fname in dir(filters):                      # Get all attributes of the "filters" module
    if not fname.startswith('j2_'):               # Filters have to start with 'j2_' prefix
      continue
    fcode = getattr(filters,fname)                # Get a pointer to filter function
    ENV.filters[fname.replace('j2_','')] = fcode  # And define a new Jinja2 filter

"""
Render a Jinja2 template

Template parameters:
* j2_file -- the name of the Jinja2 file
* j2_text -- the template text (potentially from a topology setting)

Path parameters:
* template_path -- fully specified template path, overrides any other combo
* path -- relative path to search in package directory or current/absolute directory
* user_template_path -- subdirectory of user directories to search (current, home)
"""

@functools.lru_cache()
def get_jinja2_env_for_path(template_path: tuple) -> Environment:
  ENV = Environment(loader=FileSystemLoader(template_path), \
          trim_blocks=True,lstrip_blocks=True, \
          undefined=make_logging_undefined(base=StrictUndefined))
  add_j2_filters(ENV)
  return ENV

def render_template(
      data: typing.Dict,
      j2_file: typing.Optional[str] = None,
      j2_text: typing.Optional[str] = None,
      path: typing.Optional[str] = None,
      extra_path: typing.Optional[list] = None) -> str:

  template_path = []
  if path is not None:
    if path [0] in ('.','/'):                             # Absolute path or path relative to current directory?
      template_path = [ path ]
    else:                                                 # Path relative to netsim module, add module path to it
      template_path = [ str(get_moddir() / path) ]

  if extra_path is not None:
    template_path = extra_path + template_path
  if debug_active('template'):
    print(f"TEMPLATE PATH for {j2_file or 'text'}: {template_path}")
  ENV = get_jinja2_env_for_path(tuple(template_path))
  if j2_file is not None:
    template = ENV.get_template(j2_file)
  elif j2_text is not None:
    template = ENV.from_string(j2_text)
  else:
    fatal('Internal error: Call to template function with missing J2 file and J2 text, aborting')
    return ""

  return template.render(**data)

#
# write_template: Applies a custom template (in_folder/j2) and writes it to the given file path (out_folder/filename)
#
def write_template(in_folder: str, j2: str, data: typing.Dict, out_folder: str, filename: str) -> None:
  if debug_active('template'):
    print(f"write_template {in_folder}/{j2} -> {out_folder}/{filename}")
  r_text = render_template(data=data,j2_file=j2,path=in_folder)       # Make sure we fail before creating any file(s)

  pathlib.Path(out_folder).mkdir(parents=True, exist_ok=True)
  out_file = f"{out_folder}/{filename}"
  create_file_from_text(out_file,r_text)
