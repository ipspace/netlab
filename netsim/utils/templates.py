#
# Common routines for Jinja2 templating operations
#
import functools
import os
import pathlib
import typing
from pathlib import Path

from box import Box
from jinja2 import Environment, FileSystemLoader

from ..augment import devices
from ..outputs import common as outputs_common
from . import filters, log
from . import strings as _strings
from .files import create_file_from_text, find_file, get_moddir


def add_j2_filters(ENV: Environment) -> None:
  for fname,fcode in filters.UTILS_FILTERS.items():         # Iterate over internal filter definitions
    ENV.filters[fname] = fcode                              # ... emulating the ansible.utils filters we use
    ENV.filters[f'ansible.utils.{fname}'] = fcode           # ... define simple filter name and its Ansible FQFN
    ENV.filters[f'ansible.netcommon.{fname}'] = fcode       # ... plus the obsolete FQFN


  for fname,fcode in filters.BUILTIN_FILTERS.items():       # Do the same for ansible.builtin filters we use
    ENV.filters[fname] = fcode
    ENV.filters[f'ansible.builtin.{fname}'] = fcode
  
  # Add fail() as a global function for template validation
  ENV.globals['fail'] = filters.j2_fail

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
          undefined=filters.j2_Undefined)
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

  if log.debug_active('template'):
    print(f"Template path for {j2_file or 'text'}:")
    for item in template_path:
      print(f"- {item}")

  ENV = get_jinja2_env_for_path(tuple(template_path))
  if j2_file is not None:
    template = ENV.get_template(j2_file)
  elif j2_text is not None:
    template = ENV.from_string(j2_text)
  else:
    log.fatal('Internal error: Call to template function with missing J2 file and J2 text, aborting')
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
  if log.debug_active('template'):
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
    path_prefix += [ str(get_moddir() / 'ansible') ]

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
  node._template_vars.custom_config = cfg_name
  try:
    return _strings.eval_format(f_name,node._template_vars)
  except Exception as ex:
    log.error(
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
  if log.debug_active('template'):
    print(f'Searching for {fname} template for {node.name}/{node.device} in:')
    for p in path:
      print(f'- {p}')

  if fname in node.get('config',[]):                    # Are we dealing with extra-config template?
    if fname.endswith('.j2'):                           # If the user specified a Jinja2 filename
      n_list = [ fname ]                                # ... stop guessing and just use it
    else:                                               # Otherwise, iterate through the whole list
      n_list = topology.defaults.paths.custom.f_files   # ... of potential file names
  else:
    n_list = [ fname + '.j2'] + topology.defaults.paths.t_files.f_files

  if log.debug_active('template'):
    print(f'Candidate file names:')
    for n_c in n_list:
      print(f'- {n_c}')

  for n_candidate in n_list:
    n_eval = template_lookup_name(n_candidate,fname,node,topology)
    if log.debug_active('template'):
      print(f'{n_candidate} -> {n_eval}')
    found_file = find_file(n_eval,path)
    if found_file:
      if log.debug_active('template'):
        print(f'Found file: {found_file}')
      return found_file

  return None

"""
template_shared_data: create or retrieve shared data used by all configuration templates
"""
TEMPLATE_SHARED_DATA: typing.Optional[dict] = None

def template_shared_data(topology: Box) -> dict:
  global TEMPLATE_SHARED_DATA
  if TEMPLATE_SHARED_DATA is not None:            # Detect multiple topologies used in the same process
    if topology.defaults._cache.timestamp != TEMPLATE_SHARED_DATA['_timestamp']:
      TEMPLATE_SHARED_DATA = None

  if TEMPLATE_SHARED_DATA is None:
    host_addrs = outputs_common.get_host_addresses(topology).to_dict()
    TEMPLATE_SHARED_DATA = {                      # Create the shared data we need for config templates
      'hostvars': topology.nodes.to_dict(),
      'hosts': host_addrs,                        # Deprecated value
      'host_addrs': host_addrs,                   # New value that does not clash with Ansible
      'addressing': topology.addressing.to_dict(),
      '_timestamp': topology.defaults._cache.timestamp
    }

  return TEMPLATE_SHARED_DATA

"""
template_node_data: node data with extra Ansible-like attributes used in config templates or template paths
"""
def template_node_data(n_data: Box, topology: Box) -> dict:
  node_data = outputs_common.adjust_inventory_host(         # Add group variables to node data
                            node=n_data,
                            defaults=topology.defaults,
                            group_vars=True,
                            template_vars=True).to_dict()
  shared_data = template_shared_data(topology)
  for k,v in shared_data.items():                           # ...copy shared data
    node_data[k] = v

  # ... and add provider info
  node_data['node_provider'] = devices.get_provider(n_data,topology.defaults)
  return node_data

"""
render_config_template: create an output file from the specified config template
"""
def render_config_template(
      node: Box,
      node_dict: typing.Optional[dict],
      template_id: str,
      template_path: str,
      output_file: str,
      provider_path: str,
      topology: Box) -> bool:

  if node_dict is None:
    node_dict = template_node_data(node,topology)
  try:
    node_paths = config_template_paths(
                    node=node,
                    fname=template_id,
                    topology=topology,
                    provider_path=provider_path)
    write_template(
      in_folder=os.path.dirname(template_path),
      j2=os.path.basename(template_path),
      data=node_dict,
      out_folder=os.path.dirname(output_file),
      filename=os.path.basename(output_file),
      extra_path=node_paths)
    return True
  except Exception as ex:                               # Gee, we failed
    short_path = template_path.replace(str(get_moddir()),'package:')
    log.error(                                          # Report an error and move on
      text=f"Error rendering template {template_id} for node {node.name}/device {node.device}",
      more_data=[f'Template source: {short_path}',f'error: {str(ex)}'] + template_error_location(ex),
      module='initial',
      category=log.IncorrectValue)
    return False

"""
Given the node data and module/template name, create a node config file
"""
def create_config_file(
      node: Box,
      node_dict: dict,
      topology: Box,
      module: str,
      provider_path: str,
      output_path: Path,
      output_file: str) -> bool:

  t_path = find_provider_template(
              node=node,
              fname=module,
              topology=topology,
              provider_path=provider_path)

  if not t_path:
    log.error(
      f'Cannot find {module} configuration template for {node.name}/device {node.device}',
      module='configs',
      more_hints=["Use the '--debug template' option if you're troubleshooting custom configuration templates"])
    return False

  OK = render_config_template(              # ... node.template.cfg/sh file in the output directory
          node=node,
          node_dict=node_dict,
          template_id=module,
          template_path=t_path,
          output_file=str(output_path / output_file),
          provider_path=provider_path,
          topology=topology)
  
  if OK and log.VERBOSE:
    log.info(f"Rendered {module} template for {node.name} into {output_file}")

  return OK
