'''
Topology-level transformation:

* Check for required elements (nodes, defaults)
* Check for extraneous elements
* Adjust 'provider' parameter
* Create expanded topology file in YAML format (mostly for troubleshooting purposes)
'''

import os

from box import Box

# Related modules
from .. import common

#
# Extend link/node/global attribute lists with extra attributes
#
def extend_attribute_list(settings: Box, attribute_path: str = 'topology.defaults', always_valid: list = []) -> None:
  if not 'extra_attributes' in settings:
    return

  for k in settings.extra_attributes.keys():           # Iterate over extensions
    if not k in settings.get('attributes',{}):         # Check that the extension is valid
      if k in always_valid:                            # ... some extensions are always valid (needed for modules)
        settings.attributes[k] = []                    # ... in which case we have to start with an empty list
      else:                                            # ... for everything else, throw an error
        common.error(
          f'Invalid extra_attribute {k} -- not present in configurable {attribute_path} attributes',
          common.IncorrectValue,
          'topology')

    common.must_be_list(                               # Make sure the extension is a list so it's safe to iterate over
      parent = settings.extra_attributes,
      key = k,
      path = f'{attribute_path}.extra_attributes.{k}')

    common.exit_on_error()

    for v in settings.extra_attributes[k]:             # Have to iterate over values in the custom attribute list
      if not v in settings.attributes[k]:              # ... to prevent duplicate values in attribute lists
        settings.attributes[k].append(v)               # Going through sets is not an option due to element rearrangements

#
# Extend attribute lists for all top-level elements of the defaults dictionary
# with 'attributes' and 'extra_attributes' keys
#
def extend_module_attribute_list(topology: Box) -> None:
  for k in topology.defaults.keys():
    if isinstance(topology.defaults[k],dict):
      if 'extra_attributes' in topology.defaults[k]:
        if not 'attributes' in topology.defaults[k]:   # pragma: no cover (things would break way before this point)
          topology.defaults[k].attributes = {}
        extend_attribute_list(topology.defaults[k],f'topology.defaults.{k}',['global','node','link'])

def check_required_elements(topology: Box) -> None:
  invalid_topo = False
  for rq in ['nodes']:
    if not rq in topology:
      common.error(f"Lab topology is missing mandatory {rq} element",category=common.MissingValue,module="topology")
      invalid_topo = True
    elif not topology.get(rq):
      common.error(f"Required topology element {rq} is empty",category=common.MissingValue,module="topology")
      invalid_topo = True

  if invalid_topo:
    common.fatal("Fatal topology errors, aborting")

  if not 'name' in topology:
    topo_name = os.path.basename(os.path.dirname(os.path.realpath(topology['input'][0])))
    topology.name = topo_name

  if 'module' in topology:
    common.must_be_list(topology,'module','')
    topology.defaults.module = topology.module

  topology.defaults.name = topology.name

def check_global_elements(topology: Box) -> None:
  topo_elements = topology.defaults.attributes.get('global',[]) + topology.defaults.attributes.get('internal',[])
  if topology.get('module'):
    topo_elements = topo_elements + topology.module

  for k in topology.keys():
    if not k in topo_elements:
      common.error("Unknown top-level element %s" % k,category=common.IncorrectValue,module="topology")
#
# Find virtualization provider, set provider and defaults.provider to that value
#
# Note: defaults.provider is needed in some output routines that get defaults data structure
# but not the whole topology
#
def adjust_global_parameters(topology: Box) -> None:
  if not 'provider' in topology:
    topology.provider = topology.defaults.provider
  else:
    topology.defaults.provider = topology.provider

  if not topology.provider:
    common.fatal('Virtualization provider is not defined in either "provider" or "defaults.provider" elements')

  providers = topology.defaults.providers
  if not topology.provider in providers:
    plist = ', '.join(providers.keys())
    common.fatal('Unknown virtualization provider %s. Supported providers are: %s' % (topology.provider,plist))

  # Adjust defaults with provider-specific defaults
  #
  for k in ['addressing']:
    if k in topology.defaults.providers[topology.provider]:
      topology.defaults[k] = topology.defaults[k] + topology.defaults.providers[topology.provider][k]

#
# Cleanup the topology
#

def cleanup_topology(topology: Box) -> Box:
  topo_copy = Box(topology)

  # Remove PFX generators from addressing section
  #
  for k,v in topo_copy.addressing.items():
    for p in list(v.keys()):
      if "_pfx" in p or "_eui" in p:
        v.pop(p,None)

  return topo_copy
