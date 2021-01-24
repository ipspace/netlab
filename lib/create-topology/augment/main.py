#
# Build full-blown topology data model from high-level topology
#

import netaddr
import common
import addressing
import os
import augment.topology
import augment.nodes
import augment.links

def transform(topology):
  augment.topology.check_required_elements(topology)
  augment.topology.adjust_global_parameters(topology)
  common.exit_on_error()

  topology['nodes'] = augment.nodes.adjust_node_list(topology['nodes'])
  common.exit_on_error()
  if 'links' in topology:
    topology['links'] = augment.links.adjust_link_list(topology['links'])
  common.exit_on_error()

  if not 'defaults' in topology:
    topology['defaults'] = {}
  addressing.setup(topology,topology['defaults'])

  ndict = augment.nodes.transform(topology,topology['defaults'],topology['pools'])
  common.exit_on_error()
  if 'links' in topology:
    augment.links.transform(topology['links'],topology['defaults'],ndict,topology['pools'])
  common.exit_on_error()
  del topology['pools']
