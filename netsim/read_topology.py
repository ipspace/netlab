#
# Read topology and default settings files
#
import os
import sys
import yaml
from box import Box
from importlib import resources

# Related modules
from . import common

#
# Read YAML from file, package file, or string
#
def read_yaml(filename=None,string=None):
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
  return data

def include_defaults(topo,fname):
  defaults = read_yaml(fname)
  if defaults:
    topo.input.append(fname)
    topo.defaults = defaults + topo.defaults

def load(fname,defaults,settings):
  topology = read_yaml(fname)
  if topology is None:
    common.fatal('Cannot read topology file: %s' % sys.exc_info()[0]) # pragma: no cover -- sanity check, getting here would be hard
  topology.input = [ fname ]
  topology.setdefault('defaults',{})
  topology.setdefault('includes',[ 'defaults', 'global_defaults' ])
  if not isinstance(topology.includes,list):
    common.error( \
      "Topology 'includes' element (if present) should be a list", \
      category=common.IncorrectValue,module="topology")
    topology.includes = []

  if defaults and 'defaults' in topology.includes:
    include_defaults(topology,defaults)

  if settings and 'global_defaults' in topology.includes:
    include_defaults(topology,settings)

  return topology
