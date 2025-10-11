#
# Create generic graph from lab topology
#
import typing

from box import Box

from ..data import get_box, get_empty_box
from ..data.types import must_be_list
from ..utils import log
from ..utils import routing as _routing

SHARED_GRAPH_ATTRIBUTES: Box                      # Graph attributes shared between all graph output modules

def set_shared_attributes(topology: Box) -> None:
  global SHARED_GRAPH_ATTRIBUTES
  SHARED_GRAPH_ATTRIBUTES = topology.defaults.outputs.graph.attributes.shared

"""
Utility function: map shared attributes (color, fill, width) into GL-specific attributes
"""
def map_style(g_attr: Box, style_map: Box) -> Box:
  return get_box({ style_map[k]:v for k,v in g_attr.items() if k in style_map })

"""
Build graph nodes data structure (first step in graph-building)

* Copy shared graph attributes into GL-specific ones
* Collect nodes into graph.nodes dict
* Collect BGP AS into graph.bgp dict
* Return the new graph data structure
"""
def build_nodes(topology: Box, g_type: str) -> Box:
  global SHARED_GRAPH_ATTRIBUTES
  maps = Box({},default_box=True,box_dots=True)
  for name,n in topology.nodes.items():
    if g_type != 'graph':
      for kw in SHARED_GRAPH_ATTRIBUTES:
        if kw in n.get('graph',{}) and kw not in n.get(g_type,{}):
          n[g_type][kw] = n.graph[kw]
    maps.nodes[name] = n

  if 'bgp' in topology.get('module',[]):
    for name,n in topology.nodes.items():
      bgp_as = n.get('bgp.as',None)
      if bgp_as:
        map_asn = f'AS_{bgp_as}'
        maps.bgp[map_asn].nodes[n.name] = n
        maps.bgp[map_asn].title = f'AS {bgp_as}'

  if topology.get('bgp.as_list'):
    for (asn,asdata) in topology.bgp.as_list.items():
      map_asn = f'AS_{asn}'
      if 'name' in asdata and map_asn in maps.bgp:
        maps.bgp[map_asn].title = f'{asdata.name} (AS {asn})'

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

"""
Create graph clusters:

* Use 'groups' when available
* Use BGP AS otherwise (if the topology is using BGP)
"""
def graph_clusters(graph: Box, topology: Box, settings: Box) -> None:
  if 'groups' in settings:
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

"""
Propagate link graph attributes to interfaces
"""
def propagate_link_attributes(link: Box,g_type: str, attr_list: list) -> None:
  l_attr = get_graph_attributes(link,g_type,attr_list)
  if not l_attr:
    return

  for intf in link.interfaces:
    intf[g_type] = l_attr + intf[g_type]

"""
Append an edge to the graph
"""
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
    for kw in ['type','_subnet','vrf']:
      if kw in intf:
        e_data[kw] = intf[kw]

    nodes.append(e_data)

  graph.edges.append({'nodes': nodes, 'attr': e_attr})

"""
Set interface 'type' based on VLAN attributes
"""
def set_vlan_type(intf: Box) -> None:
  if 'vlan.trunk' in intf:
    intf.type = 'vlan_trunk'
  elif 'vlan.access' in intf:
    intf.type = 'vlan_access'

"""
Append a LAN segment to the graph
"""
LINK_DEFAULTS: dict = { 'graph.rank': 100, 'graph.linkorder': 100 }

def append_segment(graph: Box,link: Box, g_type: str, topology: Box) -> None:
  link.node = link.get('bridge',f'{link.type}_{link.linkindex}')
  link.name = link.node
  link.device = 'link'
  for dk,dv in LINK_DEFAULTS.items():
    if dk not in link:
      link[dk] = dv

  graph.nodes[link.node] = link
  for af in ['ipv4','ipv6']:
    if af in link.prefix:
      link[af] = link.prefix[af]
      link._subnet = True

  for intf in link.interfaces:
    e_data = [ intf, link ]
    e_data.sort(key = lambda x: x.get('graph.rank',topology.nodes[intf.node].get('graph.rank',100)))
    e_data.sort(key = lambda x: get_attr(x,g_type,'linkorder',50))
    append_edge(graph,e_data[0],e_data[1],g_type)

def topo_edges(graph: Box, topology: Box, settings: Box,g_type: str) -> None:
  graph.edges = []
  for link in sorted(topology.links,key=lambda x: get_attr(x,g_type,'linkorder',100)):
    propagate_link_attributes(link,g_type,['linkorder','type'])

    if settings.get('topology.vlan',False):
      for intf in link.interfaces:
        set_vlan_type(intf)

    if len(link.interfaces) == 2 and link.get('graph.type','') != 'lan':
      intf_list = sorted(link.interfaces,key=lambda intf: topology.nodes[intf.node].get('graph.rank',100))
      intf_list.sort(key = lambda x: get_attr(x,g_type,'linkorder',50))
      append_edge(graph,intf_list[0],intf_list[1],g_type)
    else:
      append_segment(graph,link,g_type,topology)

def topology_graph(topology: Box, settings: Box,g_type: str) -> Box:
  set_shared_attributes(topology)
  graph = build_nodes(topology,g_type)
  graph_clusters(graph,topology,settings)
  topo_edges(graph,topology,settings,g_type)
  log.exit_on_error()
  return graph

def bgp_sessions(graph: Box, topology: Box, settings: Box, g_type: str) -> None:
  rr_sessions = settings.get('bgp.rr',None)
  no_vrf = settings.get('bgp.novrf',None)
  add_vrf = settings.get('bgp.vrf',None)
  bgp_af = settings.get('bgp.af')
  node_order = list(topology.nodes.keys())
  for n_name,n_data in topology.nodes.items():
    if 'bgp' not in n_data:
      continue
    for neighbor in _routing.neighbors(n_data,vrf=True):
      is_vrf = '_vrf' in neighbor or '_src_vrf' in neighbor
      if is_vrf and no_vrf:
        continue
      if neighbor.name < n_name:
        continue
      if bgp_af:
        bgp_active = [ af for af in bgp_af                        # Service AF
                            if af in neighbor and af not in log.AF_LIST ] + \
                     [ af for af in bgp_af
                            if af in neighbor.activate ]          # Transport AF
        if not bgp_active:
          continue

      e_1 = get_box({ 'node': n_name, 'type': neighbor.type })
      if '_src_vrf' in neighbor and add_vrf:
        e_1.vrf = neighbor._src_vrf
      e_2 = get_box({ 'node': neighbor.name, 'type': neighbor.type })
      if '_vrf' in neighbor and add_vrf:
        e_2.vrf = neighbor._vrf
      dir = '<->'
      if 'ibgp' in neighbor.type:
        if n_data.bgp.get('rr',False) and not neighbor.get('rr',False):
          dir = '->'
        elif neighbor.get('rr',False) and not n_data.get('rr',False):
          dir = '->'
          e_1, e_2 = e_2, e_1
        else:
          (e_1, e_2) = sorted([e_1, e_2],key=lambda x: node_order.index(x.node))
          (e_1, e_2) = sorted([e_1, e_2],key=lambda x: topology.nodes[x.node].get('graph.rank',100))

      if rr_sessions:
        e_1[g_type].dir = dir
      append_edge(graph,e_1,e_2,g_type)

def bgp_graph(topology: Box, settings: Box, g_type: str) -> typing.Optional[Box]:
  set_shared_attributes(topology)
  if 'bgp' not in topology.module:
    log.error(
      'Cannot build a BGP graph from a topology that does not use BGP',
      category=log.IncorrectType,
      module='graph')
    return None

  if not settings.bgp.all:
    topology.nodes = { n_name:n_data for n_name,n_data in topology.nodes.items() if 'bgp' in n_data.module }

  graph = build_nodes(topology,g_type)
  graph.clusters = graph.bgp
  graph.edges = []
  bgp_sessions(graph,topology,settings,g_type)
  log.exit_on_error()
  return graph

def effective_isis_type(t1: typing.Optional[str], t2: typing.Optional[str]) -> str:
  if t1 is None or t1 == 'level-1-2':
    return t2 or 'level-1-2'
  if t2 is None or t2 == 'level-1-2':
    return t1
  
  return '' if t1 != t2 else t1

def isis_areas(topology: Box, graph: Box) -> None:
  for _,n in topology.nodes.items():
    area = n.get('isis.area',None)
    if not area:
      continue
    area_id = area.replace('.','_')
    graph.clusters[area_id].title = area
    graph.clusters[area_id].nodes[n.name] = n

def get_node_interface(topology: Box, intf: Box) -> Box:
  iflist = [ nodeif for nodeif in topology.nodes[intf.node].interfaces if nodeif.ifname == intf.ifname ]
  if not iflist:
    log.fatal(f'Internal error: cannot find {intf.ifname} in {intf.node}')

  iflist[0].node = intf.node
  return iflist[0]

def isis_edges(topology: Box, graph: Box, g_type: str) -> None:
  graph.edges = []
  for link in sorted(topology.links,key=lambda x: get_attr(x,g_type,'linkorder',100)):
    propagate_link_attributes(link,g_type,['linkorder','type'])

    isis_nodes = [ intf.node 
                    for intf in link.interfaces
                      if 'isis' in topology.nodes[intf.node].module and not intf.get('isis.passive') ]
    if not isis_nodes:
      continue

    link.interfaces = [ get_node_interface(topology,intf) for intf in link.interfaces if intf.node in isis_nodes ]
    link.interfaces = [ intf for intf in link.interfaces if 'isis' in intf ]
    for intf in link.interfaces:
      intf.type = effective_isis_type(topology.nodes[intf.node].get('isis.type',None),intf.get('isis.type',None))

    if len(link.interfaces) == 2 and len(isis_nodes) == 2 and link.get('graph.type','') != 'lan':
      e_type = effective_isis_type(link.interfaces[0].type,link.interfaces[1].type)
      for i in range(0,2):
        link.interfaces[i].type = e_type
      append_edge(graph,link.interfaces[0],link.interfaces[1],g_type)
      continue

    append_segment(graph,link,g_type,topology)
    isis_areas = set([ topology.nodes[node].get('isis.area') for node in isis_nodes ])
    if len(isis_areas) == 1:
      area_id = isis_areas.pop().replace('.','_')
      graph.clusters[area_id].nodes[link.name] = link

def isis_graph(topology: Box, settings: Box, g_type: str) -> typing.Optional[Box]:
  set_shared_attributes(topology)
  if 'isis' not in topology.module:
    log.error(
      'Cannot build an IS-IS graph from a topology that does not use IS-IS',
      category=log.IncorrectType,
      module='graph')
    return None

  if not settings.isis.all:
    topology.nodes = { n_name:n_data for n_name,n_data in topology.nodes.items() if 'isis' in n_data.module }

  graph = build_nodes(topology,g_type)
  isis_areas(topology,graph)
  graph.edges = []
  isis_edges(topology,graph,g_type)
  log.exit_on_error()
  return graph

def parse_topology_params(settings: Box, format: typing.Optional[list]) -> None:
  if not format:
    return

  for kw in format[1:]:
    if kw in ('vlan'):
      settings.topology[kw] = True
    else:
      log.error(
        'Invalid topology graph formatting parameter {kw}',
        category=log.IncorrectValue,
        module='graph',
        skip_header=True)

  if log.VERBOSE:
    log.info('topology graph parameters',more_data=settings.topology.to_yaml().split('\n'))
  log.exit_on_error()

def parse_bgp_params(settings: Box, format: typing.Optional[list]) -> None:
  if 'rr_sessions' in settings and settings.get('bgp.rr',None) is None:
    settings.bgp.rr = settings.rr_sessions

  if not format:
    return

  for kw in format[1:]:
    if kw in ('rr','vrf','novrf','all'):
      settings.bgp[kw] = True
    elif kw in log.BGP_AF:
      settings.bgp.af[kw] = True
    else:
      log.error(
        'Invalid BGP graph formatting parameter {kw}',
        category=log.IncorrectValue,
        module='graph',
        skip_header=True)

  if log.VERBOSE:
    log.info('BGP graph parameters',more_data=settings.bgp.to_yaml().split('\n'))
  log.exit_on_error()
