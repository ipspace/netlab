#
# Build full-blown topology data structures (nodes, links, global parameter) from high-level topology
#

import netaddr
import os

# Related modules
from .. import common
from .. import addressing
from .. import augment
from ..provider import Provider

'''
adjust_modules: somewhat intricate multi-step config module adjustments

* Set node default modules based on global modules
* Adjust global module list based on node modules
'''
def adjust_modules(topology):
  augment.nodes.augment_node_module(topology)
  augment.topology.adjust_modules(topology)
  augment.nodes.merge_node_module_params(topology)

def transform(topology):
  topology.setdefault('defaults',{})
  augment.topology.check_required_elements(topology)
  augment.topology.adjust_global_parameters(topology)
  topology.Provider = Provider.load(topology.provider,topology.defaults.providers[topology.provider])
  common.exit_on_error()

  topology.nodes = augment.nodes.adjust_node_list(topology.nodes)

  common.exit_on_error()
  if 'links' in topology:
    topology.links = augment.links.adjust_link_list(topology.links)
  common.exit_on_error()

  addressing.setup(topology,topology.defaults)
  adjust_modules(topology)

  ndict = augment.nodes.transform(topology,topology.defaults,topology.pools)
  common.exit_on_error()
  if 'links' in topology:
    augment.links.transform(topology.links,topology.defaults,ndict,topology.pools)
  common.exit_on_error()
  del topology.pools
  del topology.Provider
