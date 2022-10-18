#
# Test utilities
#

from netsim.augment.nodes import ghost_buster

def transformation_results_yaml(topology):
  """
  Return the results of topology transformation YAML format

  * Remove elements that are not relevant for comparison
  * Create YAML text out of the remaining dictionary
  """
  ignore:list = topology.defaults.tests.ignore or ['addressing','defaults','nodes_map','includes']
  for k in ignore:
    topology.pop(k,None)

  if 'unmanaged' in ignore:
    topology = ghost_buster(topology)

  return topology.to_yaml()
