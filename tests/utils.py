#
# Test utilities
#

import typing

import yaml
from box import Box

from netsim.augment.nodes import ghost_buster

try:
  import ruamel.yaml  # type: ignore # noqa: F401 -- detect the actual library, not just the namespace shim
  HAS_RUAMEL = True
except ImportError:
  HAS_RUAMEL = False

def clean_ruamel(data: typing.Any) -> typing.Any:
  """
  Ruamel loves to use data types derived from int/str/float. If we want to
  create YAML via PyYAML (see #3345), we need to go through the whole data
  structure and clean it up. Yeah, it will be slow. Hooray for consistency!
  """
  if not HAS_RUAMEL:
    return data
  
  if isinstance(data,bool):
    return data
  elif isinstance(data,int):
    return int(data)
  elif isinstance(data,str):
    return str(data)
  elif isinstance(data,float):
    return float(data)
  elif isinstance(data,list):
    return [ clean_ruamel(v) for v in data ]
  elif isinstance(data,dict):
    return { k:clean_ruamel(v) for k,v in data.items() }
  else:
    return data

"""
Return the results of topology transformation YAML format

* Remove elements that are not relevant for comparison
* Create YAML text out of the remaining dictionary
"""
def transformation_results_yaml(topology: Box) -> str:
  ignore:list = topology.defaults.tests.ignore or ['addressing','defaults','nodes_map','includes']
  for k in ignore:
    topology.pop(k,None)

  if 'unmanaged' in ignore:
    topology = ghost_buster(topology)

  return yaml.dump(topology.to_dict(),default_flow_style=False,width=120)
