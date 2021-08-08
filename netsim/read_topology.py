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

#
# Read YAML from file, package file, or string
#
def read_yaml(filename: typing.Optional[str] = None, string: typing.Optional[str] = None) -> typing.Optional[Box]:
  if string is not None:
    try:
      data = Box().from_yaml(yaml_string=string,default_box=True,box_dots=True,default_box_none_transform=False)
    except:                                                                    # pragma: no cover -- can't get here unless there's a package error
      common.fatal("Cannot parse YAML string: %s " % (str(sys.exc_info()[1])))
  elif filename is None:
    common.fatal("read_yaml: have no idea what to do") # pragma: no cover -- sanity check
  elif "package:" in filename:
    package = '.'.join(__name__.split('.')[:-1])
    with resources.open_text(package,filename.replace("package:","")) as fid:
      return read_yaml(string=fid.read())
  else:
    if not os.path.isfile(filename):
      if common.LOGGING or common.VERBOSE:
        print("YAML file %s does not exist" % filename) # pragma: no cover -- too hard to test to bother
      return None
    try:
      data = Box().from_yaml(filename=filename,default_box=True,box_dots=True,default_box_none_transform=False)
    except:
      common.fatal("Cannot read YAML from %s: %s " % (filename,str(sys.exc_info()[1])))

  if common.LOGGING or common.VERBOSE:
    print("Read YAML data from %s" % (filename or "string"))

  common.unroll_dots(data)
  return data

def include_defaults(topo: Box, fname: str) -> None:
  defaults = read_yaml(fname)
  if defaults:
    topo.input.append(fname)
    topo.defaults = defaults + topo.defaults

def load(fname: str , defaults: Box, settings: str) ->Box:
  topology = read_yaml(fname)
  if topology is None:
    common.fatal('Cannot read topology file: %s' % sys.exc_info()[0]) # pragma: no cover -- sanity check, getting here would be hard
  assert topology is not None
  topology.input = [ fname ]
  topology.setdefault('defaults',{})
  topology.setdefault('includes',[ 'defaults', 'global_defaults' ])
  if not isinstance(topology.includes,list):
    common.error( \
      "Topology 'includes' element (if present) should be a list", \
      category=common.IncorrectValue,module="topology")
    topology.includes = []

  if 'defaults' in topology.includes:
    local_defaults = os.path.dirname(os.path.abspath(fname))+"/topology-defaults.yml"
    user_defaults  = os.path.expanduser('~/topology-defaults.yml')
    if defaults:
      include_defaults(topology,defaults)
    elif os.path.isfile(local_defaults):
      include_defaults(topology,local_defaults)
    elif os.path.isfile(user_defaults):
      include_defaults(topology,user_defaults)

  if settings and 'global_defaults' in topology.includes:
    include_defaults(topology,settings)

  return topology

def add_cli_args(topo: Box, args: argparse.Namespace) -> None:
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
        common.set_dots(topo,k.split('.'),v)
      else:
        topo[k] = v
