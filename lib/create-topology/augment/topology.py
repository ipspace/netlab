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
  for rq in ['nodes','defaults']:
    if not rq in topology:
      common.error("Topology error: missing '%s' element" % rq)

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
  topology['provider'] = common.get_default(data=topology,key='provider',path=['defaults','provider'])
  provider = topology['provider']
  topology['defaults']['provider'] = provider

  if not provider:
    common.fatal('Virtualization provider is not defined in either "provider" or "defaults.provider" elements')

  providers = common.get_value(data=topology,path=['defaults','providers'],default={})
  if not provider in providers:
    plist = ', '.join(providers.keys())
    common.fatal('Unknown virtualization provider %s. Supported providers are: %s' % (provider,plist))
