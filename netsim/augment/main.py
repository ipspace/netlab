#
# Build full-blown topology data structures (nodes, links, global parameter) from high-level topology
#

import sys

from box import Box
from packaging import version, specifiers

from ..utils import log
from .. import augment
from .. import providers
from .. import modules
from .. import devices as quirks
from .. import __version__
from ..data import global_vars
from . import addressing

def topology_init(topology: Box) -> None:
  global_vars.init(topology)
  augment.config.attributes(topology)
  augment.devices.augment_device_settings(topology)

def check_version(topology: Box) -> None:
  if 'version' not in topology:
    return
  try:
    topo_version = str(topology.version)
    if not '=' in topo_version and not '>' in topo_version and not '<' in topo_version:
      topo_version = f'>= {topo_version}'
    topo_spec = specifiers.SpecifierSet(topo_version)
  except:
    log.fatal(f'Invalid version specified {topology.version} specified in lab topology\n{str(sys.exc_info()[1])}')

  netlab_version = version.Version(__version__)
  if 'dev' in __version__:          # Workaround: dev versions are not considered to be 'later than' previous releases :(
    netlab_version = version.Version(netlab_version.base_version)

  if not netlab_version in topo_spec:
    log.fatal(f'Lab topology cannot be processed with netlab version {__version__}, requires {topology.version}')

def transform_setup(topology: Box) -> None:
  topology_init(topology)
  augment.topology.check_required_elements(topology)
  check_version(topology)
  topology.nodes = augment.nodes.create_node_dict(topology.nodes)
  if 'links' in topology:
    augment.links.links_init(topology)

  augment.components.expand_components(topology)

  augment.plugin.init(topology)                                         # Initialize plugins very early on in case they modify extra attributes
  augment.plugin.execute('init',topology)
  augment.topology.check_tools(topology)
  log.exit_on_error()

  augment.topology.extend_attribute_list(topology.defaults)             # Attributes have to be extended before group init
  augment.topology.extend_module_attribute_list(topology)               # ... or we won't recognize node attributes in groups
  augment.groups.init_groups(topology)
  log.exit_on_error()

  augment.topology.adjust_global_parameters(topology)
  log.exit_on_error()

  augment.nodes.augment_node_provider_data(topology)
  augment.nodes.augment_node_system_data(topology)
  log.exit_on_error()

  modules.pre_default(topology)
  log.exit_on_error()

  augment.topology.check_global_elements(topology)
  augment.nodes.validate(topology)
  log.exit_on_error()

def transform_data(topology: Box) -> None:
  addressing.setup(topology)
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
  modules.post_transform(topology)
  augment.plugin.execute('post_transform',topology)
  augment.groups.node_config_templates(topology)
  providers.execute("post_transform",topology)
  log.exit_on_error()

  quirks.process_quirks(topology)
  log.exit_on_error()
  
  augment.links.cleanup(topology)
  for remove_attr in ['Plugin','pools','_Providers']:
    topology.pop(remove_attr,None)

def transform(topology: Box) -> None:
  transform_setup(topology)
  transform_data(topology)
  post_transform(topology)
