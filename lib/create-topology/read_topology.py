#
# Read topology and default settings files
#
import yaml
import common
import os
import sys

def read_yaml(fname):
  try:
    stream = open(fname,'r')
  except:
    if common.LOGGING or common.VERBOSE:
      print("Cannot open YAML file %s" % fname)
    return None

  try:
    data = yaml.load(stream,Loader=yaml.SafeLoader)
  except:
    common.fatal("Cannot read YAML from %s: %s " % (fname,str(sys.exc_info()[1])))
  stream.close()
  if common.LOGGING or common.VERBOSE:
    print("Read YAML data from %s" % fname)
  return data

def load(fname,defaults,settings):
  topology = read_yaml(fname)
  if topology is None:
    common.fatal('Cannot open topology file: %s' % sys.exc_info()[0])
  topology['input'] = [ fname ]

  if not 'defaults' in topology:
    topology['defaults'] = {}

  local_defaults = read_yaml(defaults)
  if local_defaults:
    topology['input'].append(defaults)
    topology['defaults'] = common.merge_defaults(topology['defaults'],local_defaults)

  global_defaults = read_yaml(settings)
  if global_defaults:
    topology['input'].append(os.path.relpath(settings))
    topology['defaults'] = common.merge_defaults(topology['defaults'],global_defaults)

  return topology
