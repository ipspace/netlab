#
# Topology-level data model transformation
#
# * Check for required elements (nodes, defaults)
# * Adjust 'provider' parameter
#

import netaddr
import common
import os

def check_required_elements(topology):
  invalid_topo = False
  for rq in ['nodes','defaults']:
    if not rq in topology:
      common.error("Missing '%s' element" % rq,category=common.MissingValue,module="topology")
      invalid_topo = True

  if invalid_topo:
    common.fatal("Fatal topology errors, aborting")

  if not 'name' in topology:
    topo_name = os.path.basename(os.path.dirname(os.path.realpath(topology['input'][0])))
    topology['name'] = topo_name

  topology['defaults']['name'] = topology['name']

#
# Find virtualization provider, set provider and defaults.provider to that value
#
# Note: defaults.provider is needed in some output routines that get defaults data structure
# but not the whole topology
#
def adjust_global_parameters(topology):
  topology.setdefault('provider',topology.defaults.provider)
  topology.defaults.provider = topology.provider

  if not topology.provider:
    common.fatal('Virtualization provider is not defined in either "provider" or "defaults.provider" elements')

  providers = topology.defaults.providers
  if not topology.provider in providers:
    plist = ', '.join(providers.keys())
    common.fatal('Unknown virtualization provider %s. Supported providers are: %s' % (topology.provider,plist))
