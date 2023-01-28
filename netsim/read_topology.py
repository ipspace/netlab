#
# Read topology and default settings files
#
import os
import sys
import typing
import argparse
import pathlib
import fnmatch

from box import Box
try:
  from importlib import resources
  new_resources = hasattr(resources,'files')
except ImportError:
  new_resources = False
  import importlib_resources as resources         # type: ignore

# Related modules
from . import common
from . import data
from .data import types

"""
Utility routines for include_yaml functionality
"""

def get_traversable_path(dir_name : str) -> typing.Any:
  if 'package:' in dir_name:
    dir_name = dir_name.replace('package:','')
    pkg_files: typing.Any = None

    if not new_resources:
      pkg_files = pathlib.Path(common.get_moddir())
    else:
      package = '.'.join(__name__.split('.')[:-1])
      pkg_files = resources.files(package)        # type: ignore
    if dir_name == '':
      return pkg_files
    else:
      return pkg_files.joinpath(dir_name)
  else:
    return pathlib.Path(dir_name)

def get_globbed_files(path: typing.Any, glob: str) -> list:
  if isinstance(path,pathlib.Path):
    return [ str(fname) for fname in list(path.glob(glob)) ]
  else:
    file_names = list(path.iterdir())
    return fnmatch.filter(file_names,glob)

"""
include_yaml: Include YAML snippets at any position within a YAML file

* scan all dictionaries for '_include' key
* every _include value should be a list of files to include

Glob over all files to include:
* try to read YAML file
* add contents of the YAML file as another dictionary entry, using filename
  as the key
"""

def include_yaml(data: Box, source_file: str) -> None:
  if not isinstance(data,dict):                                       # Cannot include into something that's not a dictionary
    return

  for k in data:                                                      # First do a depth-first search into the dictionary structure
    if isinstance(data[k],dict):
      include_yaml(data[k],source_file)

  if not '_include' in data:                                          # Then get out if there's nothing to do at the current level
    return

  if 'package:' in source_file:                                       # Get the relative path to included file(s)
    inc_path = 'package:' + os.path.dirname(source_file.replace('package:',''))
  else:
    inc_path = os.path.dirname(source_file)

  for inc_name in data._include:                                            # Iterate over included files
    file_path = inc_path + ('/' if '/' in inc_path else '') + os.path.dirname(inc_name)
    traversable = get_traversable_path(file_path)                           # Get a traversable object
    inc_files = get_globbed_files(traversable,os.path.basename(inc_name))   # Get all files matching the pattern
    if not inc_files:
      common.fatal('Cannot file {inc_name} to be included into {source_file}')
      return

    for file_name in inc_files:
      yaml_data = read_yaml(filename=file_name)
      if yaml_data is None:
        common.fatal('Cannot read {file_name} that should be included into {source_file}')
        return
      data[os.path.splitext(os.path.basename(file_name))[0]] = yaml_data

  data.pop('_include',None)

#
# Read YAML from file, package file, or string
#
read_cache: dict = {}

def read_yaml(filename: typing.Optional[str] = None, string: typing.Optional[str] = None) -> typing.Optional[Box]:
  global read_cache
  if string is not None:
    try:
      yaml_data = Box().from_yaml(yaml_string=string,default_box=True,box_dots=True,default_box_none_transform=False)
      return yaml_data
    except:                                                                    # pragma: no cover -- can't get here unless there's a package error
      common.fatal("Cannot parse YAML string: %s " % (str(sys.exc_info()[1])))
      return None
  elif filename is None:
    common.fatal("read_yaml: have no idea what to do") # pragma: no cover -- sanity check
    return None

  if filename in read_cache:
    return Box(read_cache[filename],default_box=True,box_dots=True,default_box_none_transform=False)

  if "package:" in filename:
    pkg_files = get_traversable_path('package:')
    with pkg_files.joinpath(filename.replace("package:","")).open('r') as fid:
      pkg_data = read_yaml(string=fid.read())
      if not pkg_data is None:
        include_yaml(pkg_data,filename)
        read_cache[filename] = Box(pkg_data)
      return pkg_data
  else:
    if not os.path.isfile(filename):
      if common.LOGGING or common.VERBOSE:
        print("YAML file %s does not exist" % filename) # pragma: no cover -- too hard to test to bother
      return None
    try:
      yaml_data = Box().from_yaml(filename=filename,default_box=True,box_dots=True,default_box_none_transform=False)
      include_yaml(yaml_data,filename)
      read_cache[filename] = Box(yaml_data)
    except:
      common.fatal("Cannot read YAML from %s: %s " % (filename,str(sys.exc_info()[1])))

  if common.LOGGING or common.VERBOSE:
    print("Read YAML data from %s" % (filename or "string"))

  data.unroll_dots(yaml_data)
  return yaml_data

def include_defaults(topo: Box, fname: str) -> None:
  defaults = read_yaml(fname)
  if defaults:
    topo.input.append(fname)
    topo.defaults = defaults + topo.defaults

def load(fname: str , local_defaults: str, sys_defaults: str) -> Box:
  topology = read_yaml(fname)
  if topology is None:
    common.fatal('Cannot read topology file: %s' % sys.exc_info()[0]) # pragma: no cover -- sanity check, getting here would be hard
  assert topology is not None
  topology.input = [ fname ]
  if not 'includes' in topology:
    topology.includes = [ 'defaults', 'global_defaults' ]
  if not isinstance(topology.includes,list):
    common.error( \
      "Topology 'includes' element (if present) should be a list", \
      category=common.IncorrectValue,module="topology")
    topology.includes = []

  if 'defaults' in topology.includes:
    if local_defaults:
      include_defaults(topology,local_defaults)
    else:
      local_defaults = os.path.dirname(os.path.abspath(fname))+"/topology-defaults.yml"
      if os.path.isfile(local_defaults):
        include_defaults(topology,local_defaults)

      for defname in ('~/.netlab.yml','~/topology-defaults.yml'):
        user_defaults  = os.path.expanduser(defname)
        if os.path.isfile(user_defaults):
          include_defaults(topology,user_defaults)
          break

  if sys_defaults and 'global_defaults' in topology.includes:
    include_defaults(topology,sys_defaults)

  return topology

def add_cli_args(topo: Box, args: typing.Union[argparse.Namespace,Box]) -> None:
  if args.device:
    topo.defaults.device = args.device

  if args.provider:
    topo.provider = args.provider

  if args.plugin:
    if common.debug_active('plugin'):
      print(f'Adding plugins from CLI arguments: {args.plugin}')
    types.must_be_list(parent=topo,key='plugin',path='',create_empty=True)
    common.exit_on_error()
    topo.plugin.extend(args.plugin)

  if args.settings:
    for s in args.settings:
      if not "=" in s:
        common.error("Invalid CLI setting %s, should be in format key=value" % s)
      (k,v) = s.split("=")
      if '.' in k:
        try:
          data.set_dots(topo,k.split('.'),v)
        except TypeError as ex:
          if 'nodes.' in k:
            common.error(
              f'Cannot set {k}:\n... nodes element must be a dictionary if you want to set values via CLI arguments',
              common.IncorrectValue,
              'cli')
          elif 'links.' in k:
            common.error(
              f'Cannot set link value {k} through CLI arguments',
              common.IncorrectValue,
              'cli')
          else:
            common.fatal(f"Cannot set topology value {k}\n... {ex}")
        except Exception as ex:
          common.fatal(f"Cannot set topology value {k}\n... {ex}")
      else:
        topo[k] = v
