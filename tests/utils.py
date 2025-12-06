#
# Test utilities
#

from netsim.augment.nodes import ghost_buster

"""
Return the results of topology transformation YAML format

* Remove elements that are not relevant for comparison
* Create YAML text out of the remaining dictionary
"""
def transformation_results_yaml(topology):
  # Remove template caches, which are specific to the directory in which the
  # tests were executed, from the test results
  #
  for n_data in topology.nodes.values():
    for p in topology.defaults.providers:
      if p in n_data:
        n_data.pop(f'{p}._template_cache')

  ignore:list = topology.defaults.tests.ignore or ['addressing','defaults','nodes_map','includes']
  for k in ignore:
    topology.pop(k,None)

  if 'unmanaged' in ignore:
    topology = ghost_buster(topology)

  return topology.to_yaml()
