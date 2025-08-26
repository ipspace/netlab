#
# Build full-blown topology data structures (nodes, links, global parameter) from high-level topology
#

from box import Box

from .. import augment, modules, providers, roles
from .. import devices as quirks
from ..data import global_vars, validate
from ..utils import log, versioning
from . import addressing

"""
Initializing the topology transformation:

* The global variables (stored in topology defaults) are initialized
* The attribute lists are adjusted
* The search paths are expanded into absolute paths and pruned
* Plugins are loaded
* Device settings are initialized, including daemon- and child device
  inheritance

Note that the plugins have to be loaded before the device settings are
inherited, or we cannot specify the new features for generic devices.
"""
def topology_init(topology: Box) -> None:
  global_vars.init(topology)
  augment.config.attributes(topology)
  augment.config.paths(topology)
  augment.plugin.init(topology)
  augment.devices.augment_device_settings(topology)

def transform_setup(topology: Box) -> None:
  topology_init(topology)                                   # Initialize variables, load plugins
  augment.topology.topology_sanity_check(topology)          # Do the basic sanity check
  versioning.check_topology_version(topology)               # Check topology/netlab version mismatch
  topology.nodes = augment.nodes.create_node_dict(topology.nodes)
  augment.groups.precheck_groups(topology)                  # Do basic sanity checks on groups
  roles.init(topology)                                      # Initialize node roles
  augment.plugin.execute('topology_expand',topology)        # Topology-expanding plugins must be called before link checks

  if 'links' in topology:
    augment.links.links_init(topology)                      # Rewrite links into canonical form

  log.exit_on_error()

  augment.components.expand_components(topology)
  augment.groups.init_groups(topology)

  augment.plugin.execute('init',topology)
  augment.topology.check_required_elements(topology)
  log.exit_on_error()

  validate.init_validation(topology)
  modules.execute_module_hooks('normalize',topology)
  log.exit_on_error()

  augment.topology.adjust_global_parameters(topology)
  augment.groups.validate_groups(topology)
  augment.groups.copy_group_data(topology)

  providers.select_primary_provider(topology)
  log.exit_on_error()

  augment.nodes.augment_node_provider_data(topology)
  augment.nodes.augment_node_system_data(topology)
  log.exit_on_error()

  modules.pre_default(topology)
  log.exit_on_error()

  augment.topology.check_global_elements(topology)
  augment.plugin.check_plugin_dependencies(topology)                    # Check plugin dependencies on other plugins and modules
  augment.tools.process_tools(topology)
  addressing.setup(topology)
  augment.nodes.validate(topology)
  log.exit_on_error()

def transform_data(topology: Box) -> None:
  log.exit_on_error()
  augment.plugin.execute('pre_transform',topology)
  modules.pre_transform(topology)
  providers.execute("pre_transform",topology)

  augment.plugin.execute('pre_node_transform',topology)
  modules.pre_node_transform(topology)
  augment.nodes.transform(topology,topology.defaults,topology.pools)
  log.exit_on_error()
  augment.plugin.execute('post_node_transform',topology)
  modules.post_node_transform(topology)
  log.exit_on_error()

  if 'links' in topology:
    augment.links.validate(topology)
    log.exit_on_error()
    augment.plugin.execute('pre_link_transform',topology)
    modules.pre_link_transform(topology)
    log.exit_on_error()
    augment.links.transform(topology.links,topology.defaults,topology.nodes,topology.pools)
    log.exit_on_error()
    augment.plugin.execute('post_link_transform',topology)

  modules.post_link_transform(topology)

def post_transform(topology: Box) -> None:
  augment.validate.process_validation(topology)
  modules.post_transform(topology)
  augment.plugin.execute('post_transform',topology)
  augment.groups.node_config_templates(topology)
  augment.nodes.cleanup(topology)
  providers.execute("post_transform",topology)
  log.exit_on_error()

  quirks.process_quirks(topology)
  log.exit_on_error()
  
  augment.links.cleanup(topology)
  augment.groups.cleanup(topology)
  modules.cleanup(topology)
  augment.plugin.execute('cleanup',topology)
  for remove_attr in ['Plugin','pools','_Providers']:
    topology.pop(remove_attr,None)

def transform(topology: Box) -> None:
  transform_setup(topology)
  transform_data(topology)
  post_transform(topology)
