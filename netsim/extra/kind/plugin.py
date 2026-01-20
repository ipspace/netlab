
from box import Box

from netsim.augment import links
from netsim.data import get_new_box

_config_name = 'kind'
_execute_after = ['node.clone', 'fabric']

def adjust_kind_nodes(node: Box, topology: Box) -> None:
  if 'module' not in node:                                  # If the cluster does not have explicit module(s)
    node.module = []                                        # ... make sure it has none

def setup_kind_cluster(node: Box, topology: Box) -> None:
  k_workers = node.get('kind.workers',0)
  node.clab['startup-config'] = f'node_files/{node.name}/initial'
  kind_name = node.name                                     # Cluster name
  k_nodes   = [f'{kind_name}-control-plane']                # List of cluster nodes, starting with control plane
  if k_workers > 0:                                         # Add workers if requested
    k_nodes.append(f'{kind_name}-worker')                   # First one is easy
    for extra_worker in range(2,k_workers + 1):             # ... but the naming scheme is a bit peculiar
      k_nodes.append(f'{kind_name}-worker{extra_worker}')

  for kn_name in k_nodes:                                   # Now create cluster nodes
    kn_data = topology.nodes[kn_name]                       # Box dictionary is created on first reference
    kn_data.name   = kn_name                                # Set node name
    kn_data.clab.kind = "ext-container"                     # ... container kind
    kn_data.clab.name = kn_name                             # ... container name (does not follow regular convention)
    kn_data.device = 'kind-node'                            # ... device = member of kind cluster
    kn_data.interfaces = []                                 # ... and no interfaces so far
    for attr in ('provider','routing','box'):               # Copy a few attributes from the cluster
      if attr in node:
        kn_data[attr] = node[attr]

  link_index = 0                                            # Create links to cluster nodes
  while link_index < len(topology.links):                   # Iterate over all links (the list might grow)
    l_data = topology.links[link_index]
    iflist = l_data.interfaces
    kind_ifidx = -1
    for (if_idx,if_data) in enumerate(iflist):              # Try to find KinD cluster in interface list
      if if_data.node == kind_name:
        kind_ifidx = if_idx
        break

    if kind_ifidx < 0:                                      # KinD cluster not attached to this link
      link_index += 1                                       # ... move on
      continue

    # LAN/stub link -- add KinD nodes to link interfaces, remove cluster node
    #
    if len(iflist) != 2 or l_data.get('type') in ['lan','stub']:
      for kn_name in k_nodes:
        iflist.append(iflist[kind_ifidx] + {'node': kn_name})
      iflist.pop(kind_ifidx)
      link_index += 1                                       # Link transformation done, move to next link
    else:                                                   # P2P link, has to be replaced
      topology.links.pop(link_index)                        # ... remove the original link to KinD cluster
      for (kn_idx,kn_name) in enumerate(k_nodes):           # ... iterate over KinD cluster nodes
        kn_link = get_new_box(l_data)                       # ... and create new link for each node
        kn_link.interfaces[kind_ifidx].node = kn_name
        kn_link._linkname = l_data._linkname + f'[{kn_idx + 1}]'
        kn_link.linkindex = links.get_next_linkindex(topology)
        topology.links.append(kn_link)                      # Finally, append newly created link

"""
Adjust KinD cluster settings before lab transformation starts
"""
def init(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if node.device != 'kind':
      continue
    adjust_kind_nodes(node,topology)                        # Initial tweaks to the KinD nodes
  return

"""
Expand 'kind' devices into KinD clusters before node transform starts
"""
def pre_node_transform(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if node.device != 'kind':
      continue
    setup_kind_cluster(node,topology)
