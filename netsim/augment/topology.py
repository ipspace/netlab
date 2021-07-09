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

topo_main_elements = ['addressing','defaults','links','module','name','nodes','provider','Provider']
topo_internal_elements = ['input','includes']

def check_required_elements(topology: Box) -> None:
  invalid_topo = False
  for rq in ['nodes','defaults']:
    if not rq in topology:
      common.error("Missing '%s' element" % rq,category=common.MissingValue,module="topology")
      invalid_topo = True

  if invalid_topo:
    common.fatal("Fatal topology errors, aborting")

  if not 'name' in topology:
    topo_name = os.path.basename(os.path.dirname(os.path.realpath(topology['input'][0])))
    topology.name = topo_name

  topology.defaults.name = topology.name
  topo_elements = topo_main_elements + topo_internal_elements
  if topology.get('module'):
    if isinstance(topology.module,str):
      topology.module = [ topology.module ]
    topology.defaults.module = topology.module
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
  topology.setdefault('provider',topology.defaults.provider)
  topology.defaults.provider = topology.provider

  if not topology.provider:
    common.fatal('Virtualization provider is not defined in either "provider" or "defaults.provider" elements')

  providers = topology.defaults.providers
  if not topology.provider in providers:
    plist = ', '.join(providers.keys())
    common.fatal('Unknown virtualization provider %s. Supported providers are: %s' % (topology.provider,plist))

  # Adjust defaults with provider-specific defaults
  #
  for k in ['devices','addressing']:
    if k in topology.defaults.providers[topology.provider]:
      topology.defaults[k] = topology.defaults[k] + topology.defaults.providers[topology.provider][k]

#
# Cleanup the topology
#

def cleanup_topology(topology: Box) -> Box:
  topo_copy = Box(topology)
  topo_copy.pop("nodes_map")

  # Remove PFX generators from addressing section
  #
  for k,v in topo_copy.addressing.items():
    for p in list(v.keys()):
      if "_pfx" in p or "_eui" in p:
        v.pop(p,None)

  return topo_copy

#
# Write expanded topology file in YAML format
#
def create_topology_file(topology: Box, fname: str) -> None:
  topo_copy = cleanup_topology(topology)
  with open(fname,"w") as output:
    output.write("# Expanded topology created from %s\n" % topology.get('input','<unknown>'))
    output.write(topo_copy.to_yaml())
    output.close()
    print("Created expanded topology file: %s" % fname)
