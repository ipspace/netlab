#
# Create D2 graph file
#
import typing

import yaml
import os
from box import Box

from ..data import get_box
from ..data.validate import must_be_list
from . import _TopologyOutput
from ..utils import files as _files
from ..utils import log
from ._graph import topology_graph,bgp_graph

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
  if not dt in settings:
    return

  dump_d2_dict(f,settings[dt],indent)

'''
Find D2-specific device type for a given node and copy device-specific attributes
into D2 object. Another convenience wrapper around copy_d2_attr and dump_d2_dict
'''
def d2_node_attr(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  d2_type = n.d2.type or ''
  copy_d2_attr(f,d2_type,settings,indent)

'''
Add D2 styling information from d2.* link/node attributes
'''
STYLE_MAP: Box
IGNORE_KW: list = ['dir', 'type', 'name']

def d2_style(f : typing.TextIO, obj: Box, indent: str) -> None:
  if 'd2' not in obj:
    return
  d2_style = { STYLE_MAP[k]:v for k,v in obj.d2.items() if k in STYLE_MAP }
  d2_extra = obj.get('d2.format',{})

  if d2_style or d2_extra:
    dump_d2_dict(f,d2_extra + { 'style': d2_style },indent)

'''
Create a node in D2 graph and add a label and styling attributes to it

indent parameter is used to create indented definitions within containers
'''
def node_with_label(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  f.write(f'{indent}{n.d2.name} {{\n')
  d2_style(f,n,indent + '  ')
  node_ip_str = ""
  node_ip = n.loopback.ipv4 or n.loopback.ipv6
  if settings.node_address_label and not settings.node_interfaces:
    if not node_ip and n.interfaces:
      node_ip = n.interfaces[0].ipv4 or n.interfaces[0].ipv6
    if node_ip:
      node_ip_str = f'\\n{node_ip}'
  f.write(f"  {indent}label: \"{n.name} [{n.device}]{node_ip_str}\"\n")
  if settings.node_interfaces:
    node_intf = f'    {indent}* Loopback: {node_ip}' if node_ip else ''
    for i in n.interfaces:
      node_intf += f'\n    {indent}* {i.ifname}: {i.ipv4 or i.ipv6 or "l2_only"}'
    f.write(f'{indent}  interfaces: |md\n{node_intf}\n{indent}  |\n')
  d2_node_attr(f,n,settings,indent+'  ')
  f.write(f'{indent}}}\n')

'''
Similar to node-with-label, create a LAN segment node in the D2 graph. Node name is
the LAN bridge name, node label is its IPv4 or IPv6 prefix.
'''
def network_with_label(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  f.write(f'{indent}{n.name} {{\n')
  if settings.node_interfaces:
    if n.prefix.ipv4 or n.prefix.ipv6:
      f.write(f'{indent}  interfaces: |md\n{indent}    {n.prefix.ipv4 or n.prefix.ipv6}\n{indent}  |\n')
  else:
    f.write(f'{indent}  label: {n.prefix.ipv4 or n.prefix.ipv6 or n.bridge}\n')
  copy_d2_attr(f,'lan',settings,'  '+indent)
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
def edge_p2p(f : typing.TextIO, l: Box, labels: typing.Optional[bool] = False) -> None:
  e_direction = ('source','target')
  dir = l.interfaces[0].get('attr.dir','--')
  f.write(f"{l.interfaces[0].d2.name} {dir} {l.interfaces[1].d2.name} {{\n")
  d2_style(f,l,'  ')
  if labels:
    for e_idx,intf in enumerate(l.interfaces):
      if '_subnet' not in intf:
        edge_label(f,e_direction[e_idx],intf,True)
  f.write("}\n")

'''
Create a group container (or ASN container)
'''
def d2_cluster_start(f : typing.TextIO, asn: str, label: typing.Optional[str], settings: Box) -> None:
  f.write(f'{asn} {{\n')
  copy_d2_attr(f,'container',settings,'-  ')
  asn = asn.replace('_',' ')
  f.write('  label: '+ (f'{label} ({asn})' if label else asn)+'\n')

'''
Create graph containers
'''
def d2_clusters(f: typing.TextIO, graph: Box, topology: Box, settings: Box) -> None:
  for c_name,c_data in graph.clusters.items():
    d2_cluster_start(f,c_name,c_data.get('name',None),settings)
    for n in c_data.nodes.values():
      node_with_label(f,n,settings,'  ')          # Create a node within a cluster
      n_data = graph.nodes[n.name]                # Get pointer to graph node data
      n_data.d2.name = f'{c_name}.{n.name}'       # Change the D2 node name that will be used in connections
      n_data.d2.cluster = c_name                  # ... and mark it's part of a cluster

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
    edge_p2p(f,fake_link,settings.interface_labels)

def graph_topology(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  graph = topology_graph(topology,settings,'d2')
  f = _files.open_output_file(fname)

  d2_clusters(f,graph,topology,settings)
  d2_nodes(f,graph,topology,settings)
  d2_links(f,graph,topology,settings)

  if fname != '-':
    f.close()
  return True

def graph_bgp(topology: Box, fname: str, settings: Box, g_format: typing.Optional[list]) -> bool:
  rr_session = settings.get('rr_sessions',False)
  if g_format is not None and len(g_format) > 1:
    rr_session = g_format[1] == 'rr'

  graph = bgp_graph(topology,settings,'d2',rr_sessions=rr_session)
  if graph is None:
    return False

  f = _files.open_output_file(fname)

  d2_clusters(f,graph,topology,settings)
  d2_nodes(f,graph,topology,settings)

  for edge in graph.edges:
    if edge.nodes[0].type in settings:
      edge.attr.format = settings[edge.nodes[0].type] + edge.attr.format

  d2_links(f,graph,topology,settings)

  if fname != '-':
    f.close()
  return True

graph_dispatch = {
  'topology': graph_topology,
  'bgp': graph_bgp
}

'''
Set node attributes needed by D2 output module:

* D2 shape name used in connections -- set to node name, can be modified to include container name
* D2 shape type -- used to copy D2 style attributes from system defaults to D2 graph file
'''
def set_d2_attr(topology: Box) -> None:
  global STYLE_MAP
  STYLE_MAP = topology.defaults.outputs.d2.styles

  for n,ndata in topology.nodes.items():
    dev_data = topology.defaults.devices[ndata.device]
    ndata.d2.type = dev_data.graphite.icon or 'router'
    ndata.d2.name = n

class Graph(_TopologyOutput):

  DESCRIPTION :str = 'Topology graph in D2 format'

  def write(self, topology: Box) -> None:
    graphfile = self.settings.filename or 'graph.d2'
    output_format = 'topology'

    topology = get_box(topology)                       # Create a local copy of the topology
    set_d2_attr(topology)
    if hasattr(self,'filenames'):
      graphfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,'d2')

    if self.format:
      output_format = self.format[0]

    if output_format in graph_dispatch:
      if graph_dispatch[output_format](topology,graphfile,self.settings,self.format):
        log.status_created()
        print(f"graph file {graphfile} in {output_format} format")
    else:
      formats = ', '.join(graph_dispatch.keys())
      log.error('Unknown graph format, use one of %s' % formats,log.IncorrectValue,'d2')
