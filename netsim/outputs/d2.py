#
# Create D2 graph file
#
import typing

from box import Box

from ..data import get_box
from ..utils import files as _files
from ..utils import log
from . import _TopologyOutput
from ._graph import bgp_graph, isis_graph, map_style, parse_bgp_params, parse_topology_params, topology_graph

'''
Copy default settings into a D2 map converting Python dictionaries into
dotted-name format D2 is using
'''
def dump_d2_dict(f : typing.TextIO, data: dict, indent: str) -> None: 
  for k,v in data.items():
    if isinstance(v,dict):
      dump_d2_dict(f,v,f'{indent}{k}.')
    else:
      v = f'"{v}"' if isinstance(v,str) else v
      f.write(f"{indent}{k}: {v}\n")

'''
Copy named D2 default settings into D2 output file. Just a convenience
wrapper around dump_d2_dict
'''
def copy_d2_attr(f : typing.TextIO, dt: str, settings: Box, indent: str = '') -> None: 
  if not dt in settings.styles:
    return

  dump_d2_dict(f,settings.styles[dt],indent)

'''
Add D2 styling information from d2.* link/node attributes
'''
STYLE_MAP: Box
IGNORE_KW: list = ['dir', 'type', 'name']

def d2_style(f : typing.TextIO, obj: Box, indent: str, settings: Box, *, def_style: typing.Optional[str] = None) -> None:
  d2_type  = obj.get('d2.type','')
  if d2_type in settings.styles or def_style is None:
    obj_style = get_box(settings.styles.get(d2_type,{}))
  else:
    obj_style = get_box(settings.styles.get(def_style,{}))
  if 'd2' in obj:
    obj_style.style += map_style(obj.d2,STYLE_MAP)
    obj_style += obj.get('d2.format',{})
  if obj_style:
    dump_d2_dict(f,obj_style,indent)

'''
Create a node in D2 graph and add a label and styling attributes to it

indent parameter is used to create indented definitions within containers
'''
def node_with_label(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  f.write(f'{indent}{n.d2.name} {{\n')
  d2_style(f,n,indent + '  ',settings,def_style='node')
  node_ip_str = ""
  node_ip = n.loopback.ipv4 or n.loopback.ipv6
  if settings.node_address_label:
    if not node_ip and n.interfaces:
      node_ip = n.interfaces[0].ipv4 or n.interfaces[0].ipv6
    if node_ip:
      node_ip_str = f'\\n{node_ip}'
  f.write(f"  {indent}label: \"{n.name} [{n.device}]{node_ip_str}\"\n")
  f.write(f'{indent}}}\n')

'''
Similar to node-with-label, create a LAN segment node in the D2 graph. Node name is
the LAN bridge name, node label is its IPv4 or IPv6 prefix.
'''
def network_with_label(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  f.write(f'{indent}{n.name} {{\n')
  f.write(f'{indent}  label: {n.prefix.ipv4 or n.prefix.ipv6 or n.bridge}\n')
  if 'type' not in n:
    n.type = 'lan'
  if 'd2.type' not in n:
    n.d2.type = n.type
  d2_style(f,n,indent + '  ',settings)
  f.write(f'{indent}}}\n')
#  f.write('style=filled fillcolor="%s" fontsize=11' % (settings.colors.get("stub","#d1bfab")))

'''
Add an arrowhead label to a connection
'''
def edge_label(f : typing.TextIO, direction: str, data: Box, subnet: bool = True) -> None:
  f.write(f"  {direction}-arrowhead.label: '{data.label}'\n")

'''
Create a P2P connection between two nodes
'''
def edge_p2p(f : typing.TextIO, l: Box, settings: Box, labels: typing.Optional[bool] = False) -> None:
  e_direction = ('source','target')
  dir = l.interfaces[0].get('attr.dir','--')
  f.write(f"{l.interfaces[0].d2.name} {dir} {l.interfaces[1].d2.name} {{\n")
  d2_style(f,l,'  ',settings,def_style='edge')
  if labels:
    for e_idx,intf in enumerate(l.interfaces):
      if '_subnet' not in intf:
        edge_label(f,e_direction[e_idx],intf,True)
  f.write("}\n")

'''
Create a group container (or ASN container)
'''
def d2_cluster_start(
      f : typing.TextIO,
      settings: Box,
      asn: str, 
      label: typing.Optional[str] = None,
      title: typing.Optional[str] = None) -> None:
  f.write(f'{asn} {{\n')
  copy_d2_attr(f,'container',settings,'  ')
  asn = asn.replace('_',' ')
  if not title:
    title = f'{label} ({asn})' if label else asn
  f.write(f'  label: {title}\n')

'''
Create graph containers
'''
def d2_clusters(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for c_name,c_data in graph.clusters.items():
    d2_cluster_start(f,asn=c_name,label=c_data.get('name',None),title=c_data.get('title',None),settings=settings)
    for n in c_data.nodes.values():
      if 'prefix' in n:
        network_with_label(f,n,settings)
      else:
        node_with_label(f,n,settings)
      n_data = graph.nodes[n.name]                # Get pointer to graph node data
      n_data.d2.name = f'{c_name}.{n.name}'       # Change the D2 node name that will be used in connections
      n_data.d2.cluster = c_name                  # ... and mark it's part of a cluster

    f.write('}\n')

'''
Graph title
'''
def d2_graph(f: typing.TextIO, topology: Box, settings: Box) -> None:
  title = topology.get('graph.title') or topology.get('defaults.graph.title')
  if not title:
    return

  title_settings = get_box(settings)
  title_settings.styles.container = title_settings.styles.title
  d2_cluster_start(f,asn='title',title=title,settings=title_settings)
  f.write('}\n')

def d2_nodes(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for n_name,n_data in graph.nodes.items():
    if 'd2.cluster' not in n_data:
      n_data.d2.name = n_data.name
      if 'prefix' in n_data:
        network_with_label(f,n_data,settings)
      else:
        node_with_label(f,n_data,settings)

def d2_links(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for edge in graph.edges:
    fake_link = get_box({ 'interfaces': edge.nodes, 'd2': edge.attr })
    for intf in edge.nodes:
      intf.d2.name = intf.node
      if intf.node in graph.nodes:
        intf.d2.name = graph.nodes[intf.node].d2.name
    edge_p2p(f,fake_link,settings,settings.interface_labels)

def draw_graph(topology: Box, settings: Box, graph: Box, fname: str) -> None:
  f = _files.open_output_file(fname)
  d2_graph(f,topology,settings)
  d2_clusters(f,graph,topology,settings)
  d2_nodes(f,graph,topology,settings)
  d2_links(f,graph,topology,settings)

  if fname != '-':
    f.close()

def set_edge_attributes(topology: Box, settings: Box, graph: Box) -> None:
  for edge in graph.edges:
    for e_node in edge.nodes:
      if 'type' in e_node and e_node.type in settings.styles:
        edge.attr.format = settings.styles[e_node.type] + edge.attr.format
      if 'vrf' in e_node:
        edge.attr.format = settings.styles.vrf + edge.attr.format

def graph_topology(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  parse_topology_params(settings,g_format)
  graph = topology_graph(topology,settings,'d2')
  set_edge_attributes(topology,settings,graph)
  draw_graph(topology,settings,graph,fname)
  return True

def graph_bgp(topology: Box, fname: str, settings: Box, g_format: typing.Optional[list]) -> bool:
  parse_bgp_params(settings,g_format)
  graph = bgp_graph(topology,settings,'d2')
  if graph is None:
    return False

  set_edge_attributes(topology,settings,graph)
  draw_graph(topology,settings,graph,fname)
  return True

def graph_isis(topology: Box, fname: str, settings: Box, g_format: typing.Optional[list]) -> bool:
  parse_bgp_params(settings,g_format)
  graph = isis_graph(topology,settings,'d2')
  if graph is None:
    return False

  set_edge_attributes(topology,settings,graph)
  draw_graph(topology,settings,graph,fname)
  return True

graph_dispatch = {
  'topology': graph_topology,
  'bgp': graph_bgp,
  'isis': graph_isis
}

'''
Set node attributes needed by D2 output module:

* D2 shape name used in connections -- set to node name, can be modified to include container name
* D2 shape type -- used to copy D2 style attributes from system defaults to D2 graph file
'''
def set_d2_attr(topology: Box) -> None:
  global STYLE_MAP
  STYLE_MAP = topology.defaults.outputs.d2.style_map

  for n,ndata in topology.nodes.items():
    dev_data = topology.defaults.devices[ndata.device]
    ndata.d2.type = dev_data.graphite.icon or 'router'
    ndata.d2.name = n

class Graph(_TopologyOutput):

  DESCRIPTION :str = 'Topology graph in D2 format'

  def write(self, topology: Box) -> None:
    for kw in ['router','switch','lan','ibgp','ebgp']:
      if kw in self.settings:
        log.info(f'Attribute defaults.outputs.d2.{kw} is deprecated, use defaults.outputs.d2.styles.{kw}')
        self.settings.styles[kw] += self.settings[kw]

    graphfile = self.select_output_file('graph.d2')
    if graphfile is None:
      return

    output_format = 'topology'
    if self.format:
      output_format = self.format[0]

    topology = get_box(topology)                       # Create a local copy of the topology
    set_d2_attr(topology)

    if output_format in graph_dispatch:
      if graph_dispatch[output_format](topology,graphfile,self.settings,self.format):
        log.status_created()
        print(f"graph file {graphfile} in {output_format} format")
    else:
      formats = ', '.join(graph_dispatch.keys())
      log.error('Unknown graph format, use one of %s' % formats,log.IncorrectValue,'d2')
