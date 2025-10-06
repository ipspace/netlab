#
# Create Ansible inventory
#
import typing

from box import Box

from ..utils import files as _files
from ..utils import log
from . import _TopologyOutput
from ._graph import bgp_graph, isis_graph, map_style, parse_bgp_params, parse_topology_params, topology_graph


def edge_label(f : typing.TextIO, direction: str, data: Box, subnet: bool = True) -> None:
  addr = data.ipv4 or data.ipv6
  if isinstance(addr,str):
    if not subnet:
      addr = addr.split('/')[0]
    f.write(' %slabel="%s"' % (direction,addr))


def edge_node_net(f : typing.TextIO, link: Box, ifdata: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(' "%s" -- "%s"' % (ifdata.node,link.bridge))
  f.write(' [ ')
  if labels and 'ipv4' in ifdata and isinstance(ifdata.ipv4,str):
    edge_label(f,'tail',ifdata,subnet=False)
  f.write(' ]\n')

'''
Add graph styling information from graph.* link/node attributes
'''
STYLE_MAP: Box
IGNORE_KW: list = ['dir', 'type', 'name']

def get_gv_attr(c_data: Box, o_type: str, settings: Box) -> None:
  c_data.graph.format = settings.styles[o_type] + c_data.graph.format

def gv_multiline_attr(
      f : typing.TextIO,
      c_data: typing.Optional[Box] = None,
      attr: typing.Optional[Box] = None,
      indent: int = 2) -> None:
  
  if attr is None and isinstance(c_data,Box):
    attr = c_data.graph.format
  if attr is None:
    return

  for k,v in attr.items():
    f.write(f'{" " * indent}{k}="{v}"\n')

def gv_line_attr(
      f : typing.TextIO,
      c_data: typing.Optional[Box] = None,
      attr: typing.Optional[Box] = None,
      newline: bool = True) -> None:

  if attr is None and isinstance(c_data,Box):
    attr = c_data.graph.format
  if attr is None:
    return

  lead = " ["
  trail = ""
  for k,v in attr.items():
    f.write(f'{lead}{k}="{v}"')
    lead = " "
    trail = "]"
  f.write(trail)
  if newline:
    f.write("\n")

def gv_start(f : typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  title = topology.get('graph.title') or topology.get('defaults.graph.title')
  f.write('graph {\n')
  gv_multiline_attr(f,attr=settings.styles.graph,indent=2)
  if title:
    gv_multiline_attr(f,attr=settings.styles.title,indent=2)
    f.write(f'  label="{title}\n\n"\n')

  f.write('  node')
  gv_line_attr(f,attr=settings.styles.node,newline=True)
  f.write('  edge')
  gv_line_attr(f,attr=settings.styles.edge,newline=True)
  rank = { node.graph.rank 
              for node in graph.nodes.values()
                if 'graph.rank' in node and node.device != 'link' }
  if rank:
    f.write ('  newrank=true;\n')
    for r_val in sorted(list(rank)):
      r_nodes = [ node.name +"; "
                    for node in graph.nodes.values()
                      if node.get('graph.rank',None) == r_val and node.device != 'link' ]
      f.write(f'  {{ rank=same; {"".join(r_nodes)}}}\n')

def gv_end(f : typing.TextIO, fname: str) -> None:
  f.write('}\n')
  if fname != '-':
    f.close()

def gv_node(f : typing.TextIO, n: Box, settings: Box, indent: int = 0) -> None:
  global STYLE_MAP

  f.write(f'{" "*indent}"{n.name}" [\n')
  node_ip_str = ""
  if settings.node_address_label:
    node_ip = n.loopback.ipv4 or n.loopback.ipv6
    if not node_ip and n.interfaces:
      node_ip = n.interfaces[0].ipv4 or n.interfaces[0].ipv6
    if node_ip:
      node_ip_str = f'{node_ip}'

  gv_attr = n.get('graph.format',{})
  gv_attr.label = f"{n.name} [{n.device}]\\n{node_ip_str}"
  gv_attr += map_style(n.get('graph',{}),STYLE_MAP)
  gv_multiline_attr(f,attr=gv_attr,indent=indent + 2)
  f.write(f'{" "*indent}]\n')

def gv_network(f : typing.TextIO, n: Box, settings: Box, indent: int = 0) -> None:
  f.write(f'{" "*indent}{n.name}')
  n_type = n.get('type','stub')
  get_gv_attr(n,n_type,settings)
  if n_type != 'stub':
    get_gv_attr(n,'stub',settings)

  n.graph.format.label = n.prefix.ipv4 or n.prefix.ipv6 or n.bridge
  gv_line_attr(f,c_data=n)  

def gv_clusters(f : typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for c_name,c_data in graph.clusters.items():
    f.write(f'  subgraph cluster_{c_name} {{\n')

    get_gv_attr(c_data,'as',settings)
    label = c_data.get('name',None)
    title = c_data.get('title',None) or (f"{label} ({c_name}" if label else c_name)
    c_data.graph.format.label = title
    gv_multiline_attr(f,c_data,indent=4)
    for n in c_data.nodes.values():
      if 'prefix' in n:
        gv_network(f,n,settings,indent=4)
      else:
        gv_node(f,n,settings,indent=4)
      n_data = graph.nodes[n.name]                # Get pointer to graph node data
      n_data.graph.cluster = c_name
    f.write('  }\n')

def gv_nodes(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for _,n_data in graph.nodes.items():
    if 'graph.cluster' not in n_data:
      if 'prefix' in n_data:
        gv_network(f,n_data,settings,indent=2)
      else:
        gv_node(f,n_data,settings,indent=2)

def gv_links(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  global STYLE_MAP
  for edge in graph.edges:
    dir = edge.nodes[0].get('attr.dir','--')
    f.write(f' "{edge.nodes[0].node}" -- "{edge.nodes[1].node}"')

    attr = map_style(edge.attr,STYLE_MAP) + edge.attr.get('format',{})
    for n_data in edge.nodes:
      if 'type' in n_data:
        attr = attr + settings.styles[n_data.type]
      if 'vrf' in n_data:
        attr = attr + settings.styles.vrf

    if '<-' in dir:
      attr.arrowtail = 'normal'
      attr.dir = 'back'
    if '->' in dir:
      attr.arrowhead = 'normal'
      attr.dir = 'forward'
    if '<->' in dir:
      attr.dir = 'both'

    if settings.interface_labels:
      direction = ('tail','head')
      for i,n_data in enumerate(edge.nodes):
        if '_subnet' not in n_data and 'label'in n_data:
          attr[direction[i]+'label'] = n_data.label
    gv_line_attr(f,attr=attr)

def gv_adjust_style(settings: Box, o_type: str, adjust: dict) -> None:
  for k,v in adjust.items():
    log.info(f'Adjusting styles.{o_type}.{k} setting to {v}',module='graph')
    settings.styles[o_type].k = v

def gv_migrate_styles(settings: Box) -> None:
  if settings.interface_labels:
    gv_adjust_style(settings,'graph',{'ranksep': 1, 'nodesep': 0.5})

  for c_obj,c_val in settings.colors.items():
    a_name = 'color' if 'bgp' in c_obj else 'bgcolor'
    settings.styles[c_obj][a_name] = c_val

  for c_obj,c_val in settings.margins.items():
    settings.styles[c_obj].margin = c_val

def draw_graph(topology: Box, settings: Box, graph: Box, fname: str) -> None:
  f = _files.open_output_file(fname)
  gv_migrate_styles(settings)
  gv_start(f,graph,topology,settings)

  gv_clusters(f,graph,topology,settings)
  gv_nodes(f,graph,topology,settings)
  gv_links(f,graph,topology,settings)

  gv_end(f,fname)

def graph_topology(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  parse_topology_params(settings,g_format)
  graph = topology_graph(topology,settings,'graph')
  draw_graph(topology,settings,graph,fname)
  return True

def graph_bgp(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  parse_bgp_params(settings,g_format)
  graph = bgp_graph(topology,settings,'graph')
  if graph is None:
    return False

  draw_graph(topology,settings,graph,fname)
  return True

def graph_isis(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  graph = isis_graph(topology,settings,'graph')
  if graph is None:
    return False

  draw_graph(topology,settings,graph,fname)
  return True

graph_dispatch = {
  'topology': graph_topology,
  'bgp': graph_bgp,
  'isis': graph_isis,
}

class Graph(_TopologyOutput):

  DESCRIPTION :str = 'Topology graph in graphviz format'

  def write(self, topology: Box) -> None:
    global STYLE_MAP
    STYLE_MAP = topology.defaults.outputs.graph.style_map

    graphfile = self.select_output_file('graph.dot')
    if graphfile is None:
      return

    output_format = 'topology'
    if self.format:
      output_format = self.format[0]

    if output_format in graph_dispatch:
      if graph_dispatch[output_format](topology,graphfile,self.settings,self.format):
        log.status_created()
        print(f"graph file {graphfile} in {output_format} format")
    else:
      formats = ', '.join(graph_dispatch.keys())
      log.error('Unknown graph format, use one of %s' % formats,log.IncorrectValue,'graph')
