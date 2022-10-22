#
# Read topology and default settings files
#
import os
import sys
import typing
import argparse

from box import Box
try:
  from importlib import resources
except ImportError:
  import importlib_resources as resources # type: ignore

# Related modules
from . import common
from . import data

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
    package = '.'.join(__name__.split('.')[:-1])
    with resources.open_text(package,filename.replace("package:","")) as fid:
      pkg_data = read_yaml(string=fid.read())
      if not pkg_data is None:
        read_cache[filename] = Box(pkg_data)
      return pkg_data
  else:
    if not os.path.isfile(filename):
      if common.LOGGING or common.VERBOSE:
        print("YAML file %s does not exist" % filename) # pragma: no cover -- too hard to test to bother
      return None
    try:
      yaml_data = Box().from_yaml(filename=filename,default_box=True,box_dots=True,default_box_none_transform=False)
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
