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
Create a node in D2 graph and add a label and styling attributes to it

indent parameter is used to create indented definitions within containers
'''
def node_with_label(f : typing.TextIO, n: Box, settings: Box, indent: str = '') -> None:
  f.write(f'{indent}{n.d2.name} {{\n')
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
  f.write(f'{indent}{n.bridge} {{\n')
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
  addr = data.ipv4 or data.ipv6
  if isinstance(addr,str):
    if not subnet:
      addr = addr.split('/')[0]
    f.write(f"  {direction}-arrowhead.label: '{addr}'\n")

'''
Create a P2P connection between two nodes
'''
def edge_p2p(f : typing.TextIO, l: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(f"{l.interfaces[0].node} -- {l.interfaces[1].node} {{\n")
  if labels:
    edge_label(f,'source',l.interfaces[0],True)
    edge_label(f,'target',l.interfaces[1],True)
  f.write("}\n")

'''
Create a connection between a node and a LAN segment
'''
def edge_node_net(f : typing.TextIO, link: Box, ifdata: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(f"{ifdata.node} -> {link.bridge} {{\n")
  if labels:
    edge_label(f,'source',ifdata,False)
  f.write("}\n")

'''
Create an ASN or group container
'''
def as_start(f : typing.TextIO, asn: str, label: typing.Optional[str], settings: Box) -> None:
  f.write(f'{asn} {{\n')
  copy_d2_attr(f,'container',settings,'-  ')
  asn = asn.replace('_',' ')
  f.write('  label: '+ (f'{label} ({asn})' if label else asn)+'\n')

'''
Create a topology graph as a set of containers (groups or ASNs)
'''
def graph_clusters(f : typing.TextIO, clusters: Box, settings: Box, nodes: Box) -> None:
  for asn in clusters.keys():
    as_start(f,asn,clusters[asn].get('name',None),settings)
    for n in clusters[asn].nodes.values():
      node_with_label(f,n,settings,'  ')                    # Create a node within a cluster
      nodes[n.name].d2.name = f'{asn}.{n.name}'             # And change the D2 node name that will be used in connections
    f.write('}\n')

def build_maps(topology: Box) -> Box:
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
def add_groups(maps: Box, groups: list, topology: Box) -> None:
  if not 'groups' in topology:
    return

  placed_hosts = []
  for g,v in topology.groups.items():
    if g in groups:
      for n in v.members:
        if n in placed_hosts:
          log.error(
            f'Cannot create overlapping graph clusters: node {n} is in two groups',
            log.IncorrectValue,
            'graph')
          continue
        else:
          maps.groups[g].nodes[n] = topology.nodes[n]
          placed_hosts.append(n)

def graph_topology(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  f = _files.open_output_file(fname)
  maps = build_maps(topology)

  if 'groups' in settings:
    must_be_list(
      parent=settings,
      key='groups',path='defaults.outputs.graph',
      true_value=list(topology.get('groups',{}).keys()),
      create_empty=True,
      module='graph')
    add_groups(maps,settings.groups,topology)
    graph_clusters(f,maps.groups,settings,topology.nodes)
  elif 'bgp' in maps and settings.as_clusters:
    graph_clusters(f,maps.bgp,settings,topology.nodes)
  else:
    for name,n in topology.nodes.items():
      node_with_label(f,n,settings)

  for l in topology.links:
    for intf in l.interfaces:
      intf._topo_node = intf.node
      intf.node = topology.nodes[intf.node].d2.name
    if l.type == "p2p":
      edge_p2p(f,l,settings.interface_labels)
    else:
      l.bridge = l.name or f'{l.type}_{l.linkindex}'
      network_with_label(f,l,settings)
      for ifdata in l.interfaces:
        if ifdata._topo_node in maps.nodes:
          edge_node_net(f,l,ifdata,settings.interface_labels)

  f.close()
  return True

'''
Create a BGP session as a connection between two nodes

* Select the connection (arrow) type based on whether a connection is a RR-to-client session
* Copy IBGP or EBGP attributes to the connection

Please note that we call this function once for every pair of nodes, so it has to deal with
RR being the first (node) or the second (session) connection endpoint.
'''
def bgp_session(f : typing.TextIO, node: Box, session: Box, settings: Box, rr_session: bool, nodes: Box) -> None:
  arrow_dir = '<->'
  if rr_session:
    if session.type == 'ibgp':
      if 'rr' in node.bgp and node.bgp.rr and not 'rr' in session:
        arrow_dir = '->'
      if not 'rr' in node.bgp and 'rr' in session:
        arrow_dir = '<-'

  f.write(f'{node.d2.name} {arrow_dir} {nodes[session.name].d2.name} {{\n')
  copy_d2_attr(f,session.type,settings,'  ')
  f.write('}\n')

def graph_bgp(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  if not 'bgp' in topology.get('module',{}):
    log.error('BGP graph format can only be used to draw topologies using BGP',module='d2')
    return False

  f = _files.open_output_file(fname)

  rr_session = settings.get('rr_sessions',False)
  if g_format is not None and len(g_format) > 1:
    rr_session = g_format[1] == 'rr'

  maps = build_maps(topology)
  graph_clusters(f,maps.bgp,settings,topology.nodes)

  for name,n in topology.nodes.items():
    if 'bgp' in n:
      for neighbor in n.bgp.get('neighbors',[]):
        if neighbor.name > n.name:
          bgp_session(f,n,neighbor,settings,rr_session,topology.nodes)

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
