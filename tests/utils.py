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
    topology.pop(k,None)

  """
  Temporary: replace interfaces list within links with dictionary of node interfaces
  if 'links' in topology:
    for l in topology.links:
      for n in l.get('interfaces',[]):
        node = n.node
        n.pop('node',None)
        l[node] = n
      l.pop('interfaces',None)
  """

  """
  Temporary: replace neighbor list with neighbor dict
  for n in topology.nodes.values():
    if 'links' in n:
      for l in n.links:
        if 'neighbors' in l:
          n_dict = {}
          for ngh in l.neighbors:
            n_dict[ngh.node] = ngh
            n_dict[ngh.node].pop('node',None)
          l.neighbors = n_dict
  """

  """
  If we're using a dictionary extension that has to_yaml method use that,
  otherwise use pyyaml (hoping it won't generate extraneous attributes)
  """
  if callable(getattr(topology,"to_yaml",None)):
    return topology.to_yaml()
  else:
    return yaml.dump(topology)
