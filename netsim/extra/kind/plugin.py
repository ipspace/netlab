
from box import Box

from netsim.augment import links
from netsim.data import get_new_box

_config_name = 'kind'
_execute_after = ['node.clone', 'fabric']

def setup_kind_cluster(node: Box, topology: Box) -> None:
  k_workers = node.get('kind.workers',0)
  node.clab['startup-config'] = f'node_files/{node.name}/initial'
  kind_name = node.name
  k_nodes   = [f'{kind_name}-control-plane']
  if k_workers > 0:
    k_nodes.append(f'{kind_name}-worker')
    for extra_worker in range(2,k_workers + 1):
      k_nodes.append(f'{kind_name}-worker{extra_worker}')

  for kn_name in k_nodes:
    kn_data = topology.nodes[kn_name]
    kn_data.device = 'kind-node'
    kn_data.name   = kn_name
    kn_data.interfaces = []
    kn_data.clab.kind = "ext-container"
    kn_data.clab.name = kn_name
    for attr in ('provider','routing','box'):
      if attr in node:
        kn_data[attr] = node[attr]

  link_index = 0
  while link_index < len(topology.links):
    l_data = topology.links[link_index]
    iflist = l_data.interfaces
    kind_ifidx = -1
    for (if_idx,if_data) in enumerate(iflist):
      if if_data.node == kind_name:
        kind_ifidx = if_idx
        break

    if kind_ifidx < 0:
      link_index += 1
      continue

    if len(iflist) != 2 or l_data.get('type') in ['lan','stub']:
      for kn_name in k_nodes:
        iflist.append(iflist[kind_ifidx] + {'node': kn_name})
      iflist.pop(kind_ifidx)
    else:
      topology.links.pop(link_index)
      for (kn_idx,kn_name) in enumerate(k_nodes):
        kn_link = get_new_box(l_data)
        kn_link.interfaces[kind_ifidx].node = kn_name
        kn_link._linkname = l_data._linkname + f'[{kn_idx + 1}]'
        kn_link.linkindex = links.get_next_linkindex(topology)
        topology.links.append(kn_link)
        link_index += 1

"""
topology_expand - expand nodes with a 'kind' attribute into KinD clusters
"""
def pre_node_transform(topology: Box) -> None:
  for node in list(topology.nodes.values()):
    if node.device != 'kind':
      continue
    setup_kind_cluster(node,topology)
