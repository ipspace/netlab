#
# Build full-blown topology data structures (nodes, links, global parameter) from high-level topology
#

import sys

from box import Box

from .. import common
from .. import addressing
from .. import augment
from .. import providers
from .. import modules
from .. import devices as quirks
from ..data import global_vars

def topology_init(topology: Box) -> None:
  global_vars.init(topology)
  augment.config.attributes(topology)
  augment.devices.augment_device_settings(topology)

def transform_setup(topology: Box) -> None:
  topology_init(topology)
  augment.topology.check_required_elements(topology)
  topology.nodes = augment.nodes.create_node_dict(topology.nodes)
  if 'links' in topology:
    augment.links.links_init(topology)

  augment.components.expand_components(topology)

  augment.plugin.init(topology)                                         # Initialize plugins very early on in case they modify extra attributes
  augment.plugin.execute('init',topology)
  augment.topology.check_tools(topology)
  common.exit_on_error()

  augment.topology.extend_attribute_list(topology.defaults)             # Attributes have to be extended before group init
  augment.topology.extend_module_attribute_list(topology)               # ... or we won't recognize node attributes in groups
  augment.groups.init_groups(topology)
  common.exit_on_error()

  augment.topology.adjust_global_parameters(topology)
  common.exit_on_error()

  augment.nodes.augment_node_provider_data(topology)
  augment.nodes.augment_node_system_data(topology)
  common.exit_on_error()

  modules.pre_default(topology)
  common.exit_on_error()

  augment.topology.check_global_elements(topology)
  augment.nodes.validate(topology)
  common.exit_on_error()

def transform_data(topology: Box) -> None:
  addressing.setup(topology)
  common.exit_on_error()
  augment.plugin.execute('pre_transform',topology)
  modules.pre_transform(topology)
  providers.execute("pre_transform",topology)

  augment.plugin.execute('pre_node_transform',topology)
  modules.pre_node_transform(topology)
  augment.nodes.transform(topology,topology.defaults,topology.pools)
  common.exit_on_error()
  augment.plugin.execute('post_node_transform',topology)
  modules.post_node_transform(topology)

  if 'links' in topology:
    augment.links.validate(topology)
    common.exit_on_error()
    augment.plugin.execute('pre_link_transform',topology)
    modules.pre_link_transform(topology)
    common.exit_on_error()
    augment.links.transform(topology.links,topology.defaults,topology.nodes,topology.pools)
    common.exit_on_error()
    augment.plugin.execute('post_link_transform',topology)

  modules.post_link_transform(topology)

def post_transform(topology: Box) -> None:
  modules.post_transform(topology)
  augment.plugin.execute('post_transform',topology)
  augment.groups.node_config_templates(topology)
  providers.execute("post_transform",topology)
  common.exit_on_error()

  quirks.process_quirks(topology)
  common.exit_on_error()
  
  augment.links.cleanup(topology)
  for remove_attr in ['Plugin','pools','_Providers']:
    topology.pop(remove_attr,None)

def transform(topology: Box) -> None:
  transform_setup(topology)
  transform_data(topology)
  post_transform(topology)
