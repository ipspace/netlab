#
# Create generic graph from lab topology
#
import typing
from box import Box

from ..data import get_box,get_empty_box
from ..data.types import must_be_list
from ..utils import log

SHARED_GRAPH_ATTRIBUTES: Box                      # Graph attributes shared between all graph output modules

def set_shared_attributes(topology: Box) -> None:
  global SHARED_GRAPH_ATTRIBUTES
  SHARED_GRAPH_ATTRIBUTES = topology.defaults.outputs.graph.attributes.shared

def build_nodes(topology: Box) -> Box:
  maps = Box({},default_box=True,box_dots=True)
  for name,n in topology.nodes.items():
    maps.nodes[name] = n

  if 'bgp' in topology.get('module',[]):
    for name,n in topology.nodes.items():
      bgp_as = n.get('bgp.as',None)
      if bgp_as:
        bgp_as = f'AS_{bgp_as}'
        maps.bgp[bgp_as].nodes[n.name] = n

  if 'bgp' in topology and 'as_list' in topology.bgp:
    for (asn,asdata) in topology.bgp.as_list.items():
      if 'name' in asdata and asn in maps.bgp:
        maps.bgp[asn].name = asdata.name

  return maps

'''
add_groups -- use topology groups as graph clustering mechanism
'''
def add_groups(maps: Box, graph_groups: list, topology: Box) -> None:
  if not 'groups' in topology:
    return
  placed_hosts = []

  for g_name,g_data in topology.groups.items():
    if g_name not in graph_groups:
      continue
    for node in g_data.members:
      if node in placed_hosts:
        log.error(
          f'Cannot create overlapping graph clusters: node {node} is in two groups',
          log.IncorrectValue,
          'graph')
        continue

      maps.clusters[g_name].nodes[node] = topology.nodes[node]
      placed_hosts.append(node)

def graph_clusters(graph: Box, topology: Box, settings: Box) -> None:
  if 'groups' in settings:
    print(settings.groups)
    must_be_list(
      parent=settings,
      key='groups',path='defaults.outputs.graph',
      true_value=list(topology.get('groups',{}).keys()),
      create_empty=True,
      module='graph')
    add_groups(graph,settings.groups,topology)
  elif 'bgp' in graph and settings.as_clusters:
    graph.clusters = graph.bgp

def get_graph_attributes(obj: Box, g_type: str, exclude: list = []) -> Box:
  global SHARED_GRAPH_ATTRIBUTES

  # Get graph attributes shared in the 'graph' namespace
  #
  g_attr = { k:v for k,v in obj.get('graph',{}).items() if k in SHARED_GRAPH_ATTRIBUTES }
  g_dict = obj.get(g_type,{}) + g_attr            # Get graph-specific attributes + shared attributes
  for kw in exclude:
    if kw in g_dict:                              # Remove unwanted attributes
      g_dict.pop(kw)

  return g_dict

"""
Get a graph attribute from shared or graph-specific dictionary
"""
def get_attr(obj: Box, g_type: str, attr: str, default: typing.Any) -> typing.Any:
  return obj.get(f'{g_type}.{attr}',obj.get(f'graph.{attr}',default))

def append_edge(graph: Box, if_a: Box, if_b: Box, g_type: str) -> None:
  nodes = []
  e_attr = get_empty_box()
  for intf in (if_a, if_b):
    addr = intf.ipv4 or intf.ipv6
    if addr and 'prefix' not in intf:
      addr = addr.split('/')[0]
    intf_attr = get_graph_attributes(intf,g_type)
    e_attr += intf_attr
    e_data = get_box({
               'node': intf.node,
               'attr': intf_attr,
               'label': addr})
    for kw in ['type','_subnet']:
      if kw in intf:
        e_data[kw] = intf[kw]

    nodes.append(e_data)

  graph.edges.append({'nodes': nodes, 'attr': e_attr})

def topo_edges(graph: Box, topology: Box, settings: Box,g_type: str) -> None:
  graph.edges = []
  for link in sorted(topology.links,key=lambda x: get_attr(x,g_type,'linkorder',100)):
    l_attr = get_graph_attributes(link,g_type,['linkorder','type'])
    if l_attr:
      for intf in link.interfaces:
        intf[g_type] = l_attr + intf[g_type]

    if len(link.interfaces) == 2 and link.get('graph.type','') != 'lan':
      append_edge(graph,link.interfaces[0],link.interfaces[1],g_type)
    else:
      link.node = link.get('bridge',f'{link.type}_{link.linkindex}')
      link.name = link.node
      graph.nodes[link.node] = link
      for af in ['ipv4','ipv6']:
        if af in link.prefix:
          link[af] = link.prefix[af]
          link._subnet = True

      for intf in link.interfaces:
        e_data = [ intf, link ]
        if get_attr(intf,g_type,'linkorder',100) > get_attr(link,g_type,'linkorder',101):
          e_data = [ link, intf ]
        append_edge(graph,e_data[0],e_data[1],g_type)

def topology_graph(topology: Box, settings: Box,g_type: str) -> Box:
  set_shared_attributes(topology)
  graph = build_nodes(topology)
  graph_clusters(graph,topology,settings)
  topo_edges(graph,topology,settings,g_type)
  log.exit_on_error()
  return graph

def bgp_sessions(graph: Box, topology: Box, settings: Box, g_type: str, rr_sessions: bool) -> None:
  for n_name,n_data in topology.nodes.items():
    if 'bgp' not in n_data:
      continue
    for neighbor in n_data.bgp.get('neighbors',[]):
      if neighbor.name < n_name:
        continue

      e_1 = get_box({ 'node': n_name, 'type': neighbor.type })
      e_2 = get_box({ 'node': neighbor.name, 'type': neighbor.type })
      dir = '<->'
      if 'ibgp' in neighbor.type:
        if n_data.bgp.get('rr',False) and not neighbor.get('rr',False):
          dir = '->'
        elif neighbor.get('rr',False) and not n_data.get('rr',False):
          dir = '->'
          e_1, e_2 = e_2, e_1

      if rr_sessions:
        e_1.graph.dir = dir
      append_edge(graph,e_1,e_2,g_type)

def bgp_graph(topology: Box, settings: Box, g_type: str, rr_sessions: bool) -> typing.Optional[Box]:
  set_shared_attributes(topology)
  if 'bgp' not in topology.module:
    log.error(
      'Cannot build a BGP graph from a topology that does not use BGP',
      category=log.IncorrectType,
      module='graph')
    return None

  graph = build_nodes(topology)
  graph.clusters = graph.bgp
  graph.edges = []
  bgp_sessions(graph,topology,settings,g_type,rr_sessions)
  log.exit_on_error()
  return graph
