#
# Read topology and default settings files
#
import argparse
import os
import pickle
import sys
import typing

import yaml
from box import Box

# Related modules
from ..data import get_box
from ..data import types as _types
from ..utils import files as _files
from ..utils import log, versioning

USER_DEFAULTS: typing.Final[list] = ['./topology-defaults.yml','~/.netlab.yml','~/topology-defaults.yml']
SYSTEM_DEFAULTS: typing.Final[list] = ['/etc/netlab/defaults.yml','package:topology-defaults.yml']

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
    if "~/" in inc_name:
      file_path = os.path.dirname(os.path.expanduser(inc_name))
    else:
      file_path = inc_path + ('/' if '/' in inc_path else '') + os.path.dirname(inc_name)
    traversable = _files.get_traversable_path(file_path)                           # Get a traversable object
    inc_files = _files.get_globbed_files(traversable,os.path.basename(inc_name))   # Get all files matching the pattern
    if not inc_files:
      log.fatal(f'Cannot find file {inc_name} to be included into {source_file}','topology',header=True)
      return

    for file_name in sorted(inc_files):
      yaml_data = read_yaml(filename=file_name)
      if yaml_data is None:
        log.fatal(f'Cannot read {file_name} that should be included into {source_file}','topology',header=True)
        return

      if '_top' in yaml_data:                                   # Do we have to modify parent defaults outside of include scope?
        for k,v in yaml_data._top.items():                      # Iterate over top-level modifications
          if not k in data:                                     # New item, add it
            data[k] = v
          elif isinstance(v,Box) and isinstance(data[k],Box):   # Otherwise, we can only merge boxes
            data[k] = data[k] + v

        yaml_data.pop('_top',None)                              # And remove the out-of-scope modifications

      # Finally, insert the included file in its proper place
      data[os.path.splitext(os.path.basename(file_name))[0]] = yaml_data

  data.pop('_include',None)

#
# Read YAML from file, package file, or string
#
read_cache: dict = {}

class UniqueKeyLoader(yaml.SafeLoader):
  def construct_mapping(self, node : yaml.MappingNode, deep : bool = False) -> dict:
    mapping = []
    for key_node, value_node in node.value:
      key = self.construct_object(key_node, deep=deep)
      if key in mapping:
        log.error(f"Duplicate section in YAML file: {key}",category=log.IncorrectType,module='yaml')
        raise yaml.constructor.ConstructorError(None, None,f"Duplicate section {key}",node.start_mark)
      mapping.append(key)
    return super().construct_mapping(node, deep)

def read_yaml(filename: typing.Optional[str] = None, string: typing.Optional[str] = None) -> typing.Optional[Box]:
  global read_cache

  if string is not None:
    try:
      yaml_data = Box().from_yaml(yaml_string=string,default_box=True,box_dots=True,default_box_none_transform=False,Loader=UniqueKeyLoader)
      return yaml_data
    except:                                                                    # pragma: no cover -- can't get here unless there's a package error
      log.fatal("Cannot parse YAML string: %s " % (str(sys.exc_info()[1])))
      return None
  elif filename is None:
    log.fatal("read_yaml: have no idea what to do") # pragma: no cover -- sanity check
    return None

  if log.debug_active('defaults'):
    print(f"Reading {filename}")

  if filename in read_cache:
    return Box(read_cache[filename],default_box=True,box_dots=True,default_box_none_transform=False)

  if "package:" in filename:
    pkg_files = _files.get_traversable_path('package:')
    with pkg_files.joinpath(filename.replace("package:","")).open('r') as fid:
      pkg_data = read_yaml(string=fid.read())
      if not pkg_data is None:
        include_yaml(pkg_data,filename)
        read_cache[filename] = Box(pkg_data)
      return pkg_data
  else:
    if not os.path.isfile(filename):
      if log.LOGGING or log.VERBOSE:
        print("YAML file %s does not exist" % filename) # pragma: no cover -- too hard to test to bother
      return None
    try:
      yaml_data = Box().from_yaml(filename=filename,default_box=True,box_dots=True,default_box_none_transform=False,Loader=UniqueKeyLoader)
      include_yaml(yaml_data,filename)
      read_cache[filename] = Box(yaml_data)
    except:
      log.fatal("Cannot read YAML from %s: %s " % (filename,str(sys.exc_info()[1])))

  if log.LOGGING or log.VERBOSE:
    print("Read YAML data from %s" % (filename or "string"))

  return yaml_data

def include_defaults(topo: Box, fname: str) -> None:
  defaults = read_yaml(fname)
  if defaults:
    topo.input.append(fname)
    topo.defaults = defaults + topo.defaults

#
# Build the list of defaults
#
# The defaults are taken from defaults.sources.list (if exists) or constructed from 
#
# * Extra topology-specific sources (defaults.sources.extra)
# * User defaults (defaults.sources.user or API argument or USER_DEFAULTS)
# * System defaults (defaults.sources.system or API argument or SYSTEM_DEFAULTS)
#
# The user and system defaults should almost never be used, the viable exceptions are:
#
# * Test harness -- error cases
# * netlab show --system command
#

def build_defaults_list(
      topology: Box,
      user_defaults: typing.Optional[list] = None, 
      system_defaults: typing.Optional[list] = None) -> list:

  global USER_DEFAULTS,SYSTEM_DEFAULTS
  defaults_list = []
  if _types.must_be_list(
        parent=topology,
        key='defaults.sources.list',
        path='',
        true_value=USER_DEFAULTS + SYSTEM_DEFAULTS):
    return topology.defaults.sources.list

  if _types.must_be_list(
        parent=topology,
        key='defaults.sources.extra',
        path=''):
    defaults_list.extend(topology.defaults.sources.extra)

  if user_defaults is None:
    user_defaults = USER_DEFAULTS

  if _types.must_be_list(
        parent=topology,
        key='defaults.sources.user',
        path='',
        true_value=user_defaults):
    defaults_list.extend(topology.defaults.sources.user)
  else:
    defaults_list.extend(user_defaults)

  if system_defaults is None:
    system_defaults = SYSTEM_DEFAULTS

  if _types.must_be_list(
        parent=topology,
        key='defaults.sources.system',
        path='',
        true_value=system_defaults):
    defaults_list.extend(topology.defaults.sources.system)
  else:
    defaults_list.extend(system_defaults)

  return defaults_list

#
# include_environment_defaults -- set defaults from environment variables
#
# * Consider all environment variables starting with NETLAB_
# * Replace underscores with dots, turn string into lowercase
# * Evaluate the resulting string and store the results

def include_environment_defaults(topology: Box) -> None:
  for k in os.environ:
    v = os.environ[k]                             # Get the variable value
    try:
      v = yaml.load(v,Loader=yaml.SafeLoader)     # Try to evaluate it as bool/int/whatever
    except:
      pass                                        # Can't do that? No harm, we'll assume it's a string

    k = k.lower()                                 # Normalize to lowercase
    if not k.startswith('netlab_'):               # Skip non-netlab variables
      continue

    k = k.replace('netlab_','',1)                 # Drop the netlab_ prefix
    k = k.replace('_','.')                        # Replace underscores with dots
    k = k.replace('..','_')                       # Turn __ (..) back into a single underscore
    if log.VERBOSE > 1:
      print(f'Setting defaults.{k} to {v}')
    topology.defaults[k] = v                      # And set the value

#
# Load the topology and defaults
#
# * Read the topology from fname
# * Build the list of defaults
# * Merge all defaults with the topology
#
def load(
      fname: str,
      user_defaults: typing.Optional[list] = None, 
      system_defaults: typing.Optional[list] = None,
      relative_topo_name: typing.Optional[bool] = False) -> Box:

  if not relative_topo_name and fname.find('package:') != 0:
    fname = str(_files.absolute_path(fname))
    fname = versioning.get_versioned_topology(fname)

  topology = read_yaml(fname)
  if topology is None:
    log.fatal('Cannot read topology file: %s' % sys.exc_info()[0]) # pragma: no cover -- sanity check, getting here would be hard

  topology.input = [ fname ]
  if 'includes' in topology:                                # includes topology element SHOULD NOT BE USED
    if log.RAISE_ON_ERROR:                                  # ... and if we're under test harness
      raise log.IncorrectValue                              # ... raise a hard error
    else:
      log.fatal('The "includes" topology element shall not be used',module='topology',header=True)

  # Now build the list of default sources
  defaults_list = build_defaults_list(topology,user_defaults,system_defaults)

  if log.debug_active('defaults'):
    print(f"Defaults from {defaults_list}")

  for dfname in defaults_list:
    if dfname.find('package:') != 0:                        # Is this a package file?
      dfname = str(_files.absolute_path(dfname,fname))      # ... nope, find absolute path based on topology file name
      if not os.path.isfile(dfname):                        # And if the file doesn't exist
        continue                                            # ... skip it

    include_defaults(topology,dfname)                       # Merge the defaults

  if user_defaults or user_defaults is None:                # User defaults missing or specified?
    include_environment_defaults(topology)                  # ... we care about user defaults, add environment vars

  return topology

#
# Read just the system defaults
#
def system_defaults() -> Box:
  return load("package:cli/empty.yml",user_defaults=[])
#
# Parse values specified in CLI settings. Return string, bool or int
#
def transform_cli_value(v: str) -> typing.Union[int,bool,str]:
  try:                                            # Try to parse an integer
    return int(v)
  except:
    pass

  if v.lower() in ['true','false']:               # Recognize True or False
    return v.lower() == 'true'                    # ... and return the result of "do we have true?"
  
  return v                                        # Otherwise it's a string

def add_cli_args(topo: Box, args: typing.Union[argparse.Namespace,Box]) -> None:
  if args.device:
    topo.defaults.device = args.device

  if args.provider:
    p_list = args.provider.split(':')
    topo.provider = p_list[0]
    for p_option in p_list[1:]:
      for p_element in p_option.split(','):
        topo.defaults.providers[topo.provider][p_element] = True

  if args.plugin:
    if log.debug_active('plugin'):
      print(f'Adding plugins from CLI arguments: {args.plugin}')
    _types.must_be_list(parent=topo,key='plugin',path='',create_empty=True)
    log.exit_on_error()
    topo.plugin.extend(args.plugin)

  if args.settings:
    for s in args.settings:
      if not "=" in s:
        log.error("Invalid CLI setting %s, should be in format key=value" % s)
      (k,v) = s.split("=")
      v = transform_cli_value(v)
      try:
        topo[k] = v
      except TypeError as ex:
        if 'nodes.' in k:
          log.error(
            f'Cannot set {k}:\n... nodes element must be a dictionary if you want to set values via CLI arguments',
            log.IncorrectValue,
            'cli')
        elif 'links.' in k:
          log.error(
            f'Cannot set link value {k} through CLI arguments',
            log.IncorrectValue,
            'cli')
        else:
          log.fatal(f"Cannot set topology value {k}\n... {ex}")
      except Exception as ex:
        log.fatal(f"Cannot set topology value {k}\n... {ex}")

"""
Read pickled snapshot data
"""
def load_pickled_data(snapshot: str) -> Box:
  try:
    pfile = open(snapshot,'rb')
  except Exception as ex:
    log.fatal(f'Cannot open pickle file {pfile}: {str(ex)}')

  try:
    data = pickle.load(pfile)
    if not isinstance(data,dict):
      log.fatal(f'The picked snapshot {snapshot} contains {type(data)}, not a dictionary')
    pfile.close()
  except Exception as ex:
    log.fatal(f'Cannot read pickled data from {pfile}: {str(ex)}')

  return get_box(data)
