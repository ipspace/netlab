#
# Test utilities
#

import yaml

def transformation_results_yaml(topology,ignore=('addressing','defaults','nodes_map','includes')):
  """
  Return the results of topology transformation YAML format

  * Remove elements that are not relevant for comparison
  * Create YAML text out of the remaining dictionary
  """
  for k in ignore:
    del topology[k]


  """
  If we're using a dictionary extension that has to_yaml method use that,
  otherwise use pyyaml (hoping it won't generate extraneous attributes)
  """
  if callable(getattr(topology,"to_yaml",None)):
    return topology.to_yaml()
  else:
    return yaml.dump(topology)
