#
# Common routines for create-topology script
#
import functools
import os
import pathlib
import typing

from box import Box
from jinja2 import Environment, FileSystemLoader, StrictUndefined, make_logging_undefined

from ..augment import devices
from ..outputs import common as outputs_common
from . import filters
from . import strings as _strings
from .files import create_file_from_text, find_file, get_moddir
from .log import debug_active, error, fatal


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
    template_path += [ p for p in extra_path if p not in template_path ]

  if debug_active('template'):
    print(f"Template path for {j2_file or 'text'}:")
    for item in template_path:
      print(f"- {item}")

  ENV = get_jinja2_env_for_path(tuple(template_path))
  if j2_file is not None:
    template = ENV.get_template(j2_file)
  elif j2_text is not None:
    template = ENV.from_string(j2_text)
  else:
    fatal('Internal error: Call to template function with missing J2 file and J2 text, aborting')
    return ""

  return template.render(**data)

"""
write_template: Applies a custom template (in_folder/j2) and writes it to the given file path (out_folder/filename)
"""
def write_template(
        in_folder: str,
        j2: str,
        data: typing.Dict,
        out_folder: str,
        filename: str,
        extra_path: typing.Optional[list] = None) -> None:
  if debug_active('template'):
    print(f"write_template {in_folder}/{j2} -> {out_folder}/{filename}")
  # Make sure we fail before creating any file(s)
  r_text = render_template(data=data,j2_file=j2,path=in_folder,extra_path=extra_path)

  pathlib.Path(out_folder).mkdir(parents=True, exist_ok=True)
  out_file = f"{out_folder}/{filename}"
  create_file_from_text(out_file,r_text)

"""
template_error_location: extract the exact location of the template error from the exception traceback
"""
def template_error_location(exc: Exception) -> list:
  loc_list = []
  tb = exc.__traceback__
  while tb:
    f = tb.tb_frame
    if f.f_code.co_filename.endswith('.j2'):
      loc_txt = f'Line {tb.tb_lineno} @ {f.f_code.co_filename}'
      if loc_txt not in loc_list:
        loc_list.append(loc_txt)
    tb = tb.tb_next

  loc_list.reverse()
  return loc_list

"""
Build a list of potential directories in which we might find a configuration template

The function uses default search paths for custom- or configuration templates and augments
them with provider- and device-specific information
"""
def config_template_paths(
      node: Box,
      fname: str,
      topology: Box,
      provider_path: typing.Optional[str] = None) -> list:
  if fname in node.get('config',[]):                    # Are we dealing with extra-config template?
    path_prefix = topology.defaults.paths.custom.dirs
    path_suffix = [ fname ]
  else:
    path_suffix = [ node.device ]
    path_prefix = [ provider_path ] if provider_path else []
    path_prefix += topology.defaults.paths.templates.dirs

    if node.get('_daemon',False):
      if '_daemon_parent' in node:
        path_suffix.append(node._daemon_parent)

  return [ os.path.join(pf, sf) for pf in path_prefix for sf in path_suffix ] + path_prefix

"""
Evaluate file names used during the template lookup
"""
def template_lookup_name(f_name: str, cfg_name: str, node: Box, topology: Box) -> str:
  if '_template_vars' not in node:
    host = outputs_common.adjust_inventory_host(node,topology.defaults,translate={},ignore=[],group_vars=True)

    node._template_vars = {
      'ansible_network_os': host.ansible_network_os,
      'inventory_hostname': node.name,
      'netlab_device_type': host.get('netlab_device_type',host.get('ansible_network_os','none')),
      'node_provider': devices.get_provider(node,topology.defaults),
    }

  node._template_vars.config_module = cfg_name
  try:
    return _strings.eval_format(f_name,node._template_vars)
  except Exception as ex:
    error(
      f'Internal error: Cannot render template name for node {node.name} from {f_name}',
      more_data = [ str(ex) ],
      module='templates')
    return f_name

"""
Find a provider/daemon configuration template
"""
def find_provider_template(
      node: Box,
      fname: str,
      topology: Box,
      provider_path: typing.Optional[str] = None) -> typing.Optional[str]:

  path = config_template_paths(node,fname,topology,provider_path=provider_path)
  if debug_active('template'):
    print(f'Searching for {fname} template for {node.name}/{node.device} in:')
    for p in path:
      print(f'- {p}')

  if fname in node.get('config',[]):                    # Are we dealing with extra-config template?
    n_list = [ node.device + '.j2' ]
  else:
    n_list = [ fname + '.j2'] + topology.defaults.paths.t_files.f_files

  if debug_active('template'):
    print(f'Candidate file names:')
    for n_c in n_list:
      print(f'- {n_c}')

  for n_candidate in n_list:
    n_eval = template_lookup_name(n_candidate,fname,node,topology)
    if debug_active('template'):
      print(f'{n_candidate} -> {n_eval}')
    found_file = find_file(n_eval,path)
    if found_file:
      if debug_active('template'):
        print(f'Found file: {found_file}')
      return found_file

  return None
