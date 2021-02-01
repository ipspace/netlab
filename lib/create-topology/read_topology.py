#
# Read topology and default settings files
#
import yaml
import common
import os
import sys
from box import Box

def read_yaml(fname):
  if not os.path.isfile(fname):
    if common.LOGGING or common.VERBOSE:
      print("YAML file %s does not exist" % fname)
    return None

  try:
    data = Box().from_yaml(filename=fname,default_box=True,box_dots=True,default_box_none_transform=False)
  except:
    common.fatal("Cannot read YAML from %s: %s " % (fname,str(sys.exc_info()[1])))

  if common.LOGGING or common.VERBOSE:
    print("Read YAML data from %s" % fname)
  return data

def include_defaults(topo,fname):
  defaults = read_yaml(fname)
  if defaults:
    topo.input.append(fname)
    topo.defaults = defaults + topo.defaults

def load(fname,defaults,settings):
  topology = read_yaml(fname)
  if topology is None:
    common.fatal('Cannot read topology file: %s' % sys.exc_info()[0])
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
