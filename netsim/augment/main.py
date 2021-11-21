#
# Build full-blown topology data structures (nodes, links, global parameter) from high-level topology
#

from box import Box

from .. import common
from .. import addressing
from .. import augment
from ..providers import _Provider
from .. import modules

def transform_setup(topology: Box) -> None:
  augment.plugin.init(topology)
  augment.plugin.execute('init',topology)
  augment.topology.check_required_elements(topology)
  augment.topology.adjust_global_parameters(topology)
  topology.Provider = _Provider.load(topology.provider,topology.defaults.providers[topology.provider])
  common.exit_on_error()

  topology.nodes = augment.nodes.adjust_node_list(topology.nodes)
  common.exit_on_error()
  if 'links' in topology:
    topology.links = augment.links.adjust_link_list(topology.links)
  common.exit_on_error()

def transform_data(topology: Box) -> None:
  addressing.setup(topology,topology.defaults)
  augment.plugin.execute('pre_transform',topology)
  modules.pre_transform(topology)

  augment.groups.adjust_groups(topology)

  augment.plugin.execute('pre_node_transform',topology)
  ndict = augment.nodes.transform(topology,topology.defaults,topology.pools)
  common.exit_on_error()
  augment.plugin.execute('post_node_transform',topology)

  if 'links' in topology:
    augment.plugin.execute('pre_link_transform',topology)
    augment.links.transform(topology.links,topology.defaults,ndict,topology.pools)
    common.exit_on_error()
    augment.plugin.execute('post_link_transform',topology)

  modules.post_transform(topology)
  augment.plugin.execute('post_transform',topology)
  common.exit_on_error()

  topology.pop('Plugin',None)
  del topology.pools
  del topology.Provider

def transform(topology: Box) -> None:
  transform_setup(topology)
  transform_data(topology)
