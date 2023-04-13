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

ansible_filter_map: dict = {}
ANSIBLE_DEBUG = False

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
  global ansible_filter_map
  load_ansible_filters()

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
  for k,v in ansible_filter_map.items():
    ENV.filters[k] = v
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

"""
get_ansible_filter_map: Get a map of ansible filters to be used in jinja2 templates

Based on the tentative Python module name, this function tries to:

* Load the module
* Find the FilterModule class in that module
* Execute the filters function in that class
* Append the resulting dict to the ansible_filter_map
"""
def get_ansible_module(module_name: str) -> typing.Any:
  try:
    module = __import__(module_name)
    target = module
    for hname in module_name.split('.')[1:]:
      target = getattr(target, hname)

    return target
  except Exception as ex:
    if debug_active('template') or ANSIBLE_DEBUG:
      print(f"get_ansible_module failed to load {module_name}: {ex}")
    return None

def get_ansible_filter_map(module_name: str) -> dict:
  try:
    target = get_ansible_module(module_name)
    filter_class = getattr(target, 'FilterModule')
    filter_dict = filter_class().filters()
    return filter_dict if isinstance(filter_dict,dict) else {}
  except Exception as ex:
    if debug_active('template') or ANSIBLE_DEBUG:
      print(f"get_ansible_filter_map failed for {module_name}: {ex}")
    return {}

"""
add_ansible_filter_directory: Get all filters from an Ansible plugins/filter directory
"""
def add_ansible_filter_directory(module: typing.Any) -> None:
  try:
    for fname in list(pathlib.Path(module.__path__[0]).glob('*.py')):
      if fname.name == '__init__.py':
        continue
      filter_name = module.__package__ + '.' + fname.name.replace('.py','')
      if debug_active('template') or ANSIBLE_DEBUG:
        print(f"Trying to load filters from {filter_name}")
      add_filters(get_ansible_filter_map(filter_name))
  except Exception as ex:
    if debug_active('template') or ANSIBLE_DEBUG:
      print(f"get_ansible_filter_director failed for {module.__path__[0]}: {ex}")

"""
add_filters: add a dictionary of Jinja2 filter routines to the global filter map
"""
def add_filters(filters: dict) -> None:
  global ansible_filter_map

  for filter_name in filters:
    ansible_filter_map[filter_name] = filters[filter_name]

"""
Main 'load ansible filters' routine:

* If ansible_filter_map is already populated, return
* Try to load netaddr-related filters from various places playing whack-a-mole with Ansible developers
"""
def load_ansible_filters() -> None:
  global ansible_filter_map

  if ansible_filter_map:
    return

  filters = get_ansible_module('ansible_collections.ansible.utils.plugins.filter')
  if filters:
    add_ansible_filter_directory(filters)
    return

  add_filters(get_ansible_filter_map('ansible_collections.ansible.netcommon.plugins.filter.ipaddr'))
