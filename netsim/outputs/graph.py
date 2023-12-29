#
# Create Ansible inventory
#
import typing

import yaml
import os
from box import Box

from ..data.validate import must_be_list
from . import _TopologyOutput
from ..utils import files as _files
from ..utils import log

def node_with_label(f : typing.TextIO, n: Box, settings: Box, indent: typing.Optional[str] = '') -> None:
  f.write('%s  "%s" [\n' % (indent,n.name))
  node_ip_str = ""
  if settings.node_address_label:
    node_ip = n.loopback.ipv4 or n.loopback.ipv6
    if not node_ip and n.interfaces:
      node_ip = n.interfaces[0].ipv4 or n.interfaces[0].ipv6
    if node_ip:
      node_ip_str = f'<br /><sub>{node_ip}</sub>'

  f.write(f'{indent}    label=<{n.name} [{n.device}]{node_ip_str}>\n')
  f.write('%s    fillcolor="%s"\n' % (indent,settings.colors.get('node','#ff9f01')))
  f.write('%s  ]\n' % indent)

def network_with_label(f : typing.TextIO, n: Box, settings: Box, indent: typing.Optional[str] = '') -> None:
  f.write('%s  "%s" [' % (indent,n.bridge))
  f.write('style=filled fillcolor="%s" fontsize=11' % (settings.colors.get("stub","#d1bfab")))
  f.write(' label="%s"' % (n.prefix.ipv4 or n.prefix.ipv6 or n.bridge))
  f.write("]\n")

def edge_label(f : typing.TextIO, direction: str, data: Box, subnet: bool = True) -> None:
  addr = data.ipv4 or data.ipv6
  if isinstance(addr,str):
    if not subnet:
      addr = addr.split('/')[0]
    f.write(' %slabel="%s"' % (direction,addr))

def edge_p2p(f : typing.TextIO, l: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(f' "{l.interfaces[0].node}" -- "{l.interfaces[1].node}"')
  f.write(' [')
  if labels:
    edge_label(f,'tail',l.interfaces[0])
    edge_label(f,'head',l.interfaces[1])
  f.write(' ]\n')

def edge_node_net(f : typing.TextIO, link: Box, ifdata: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(' "%s" -- "%s"' % (ifdata.node,link.bridge))
  f.write(' [ ')
  if labels and 'ipv4' in ifdata and isinstance(ifdata.ipv4,str):
    edge_label(f,'tail',ifdata,subnet=False)
  f.write(' ]\n')

def graph_start(f : typing.TextIO) -> None:
  f.write('graph {\n')
  f.write('  bgcolor="transparent"\n')
  f.write('  node [shape=box, style="rounded,filled" fontname=Verdana]\n')
  f.write('  edge [fontname=Verdana labelfontsize=10 labeldistance=1.5]\n')

def as_start(f : typing.TextIO, asn: str, label: typing.Optional[str], settings: Box) -> None:
  f.write('  subgraph cluster_%s {\n' % asn)
  f.write('    bgcolor="%s"\n' % settings.colors.get('as','#e8e8e8'))
  f.write('    fontname=Verdana\n')
  f.write('    margin=%s\n' % settings.margins.get('as',16))
  if label:
    f.write('    label="%s (%s)"\n' % (label,asn.replace('_',' ')))
  else:
    f.write('    label="%s"\n' % asn.replace('_',' '))

def graph_clusters(f : typing.TextIO, clusters: Box, settings: Box) -> None:
  for asn in clusters.keys():
    as_start(f,asn,clusters[asn].get('name',None),settings)
    for n in clusters[asn].nodes.values():
      node_with_label(f,n,settings,'  ')
    f.write('  }\n')

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

"""
add_groups -- use topology groups as graph clustering mechanism
"""

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
  graph_start(f)

  maps = build_maps(topology)

  if 'groups' in settings:
    must_be_list(
      parent=settings,
      key='groups',path='defaults.outputs.graph',
      true_value=list(topology.get('groups',{}).keys()),
      create_empty=True,
      module='graph')
    add_groups(maps,settings.groups,topology)
    graph_clusters(f,maps.groups,settings)
  if 'bgp' in maps and settings.as_clusters:
    graph_clusters(f,maps.bgp,settings)
  else:
    for name,n in topology.nodes.items():
      node_with_label(f,n,settings)

  for l in topology.links:
    if l.type == "p2p":
      edge_p2p(f,l,settings.interface_labels)
    else:
      if not l.bridge:
        log.error('Found a lan/stub link without a bridge name, skipping',log.IncorrectValue,'graph')
        next
      network_with_label(f,l,settings)
      for ifdata in l.interfaces:
        if ifdata.node in maps.nodes:
          edge_node_net(f,l,ifdata,settings.interface_labels)

  f.write("}\n")
  f.close()
  return True

def bgp_session(f : typing.TextIO, node: Box, session: Box, settings: Box, rr_session: bool) -> None:
  arrow_dir = 'both'
  if rr_session:
    arrow_dir = 'none'
    if session.type == 'ibgp':
      if 'rr' in node.bgp and node.bgp.rr and not 'rr' in session:
        arrow_dir = 'forward'
      if not 'rr' in node.bgp and 'rr' in session:
        arrow_dir = 'back'

  f.write('  "%s" -- "%s"' % (node.name,session.name))
  f.write('  [\n')
  if session.type == 'ibgp':
    f.write('    color="%s"\n' % settings.colors.get('ibgp','#613913'))
  else:
    f.write('    color="%s"\n' % settings.colors.get('ebgp','#b21a1a'))
  f.write(f'    penwidth=2.5 arrowsize=0.7 dir={arrow_dir}\n')
  f.write('  ]\n')

def graph_bgp(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  if not 'bgp' in topology.get('module',{}):
    log.error('BGP graph format can only be used to draw topologies using BGP')
    return False

  f = _files.open_output_file(fname)
  graph_start(f)

  rr_session = g_format is not None and len(g_format) > 1 and g_format[1] == 'rr'

  maps = build_maps(topology)
  graph_clusters(f,maps.bgp,settings)

  for name,n in topology.nodes.items():
    if 'bgp' in n:
      for neighbor in n.bgp.get('neighbors',[]):
        if neighbor.name > n.name:
          bgp_session(f,n,neighbor,settings,rr_session)

  f.write("}\n")
  f.close()
  return True

graph_dispatch = {
  'topology': graph_topology,
  'bgp': graph_bgp
}

class Graph(_TopologyOutput):

  DESCRIPTION :str = 'Topology graph in graphviz format'

  def write(self, topology: Box) -> None:
    graphfile = self.settings.filename or 'graph.dot'
    output_format = 'topology'

    if hasattr(self,'filenames'):
      graphfile = self.filenames[0]
      if len(self.filenames) > 1:
        log.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),log.IncorrectValue,'graph')

    if self.format:
      output_format = self.format[0]

    if output_format in graph_dispatch:
      if graph_dispatch[output_format](topology,graphfile,self.settings,self.format):
        log.status_created()
        print(f"graph file {graphfile} in {output_format} format")
    else:
      formats = ', '.join(graph_dispatch.keys())
      log.error('Unknown graph format, use one of %s' % formats,log.IncorrectValue,'graph')
