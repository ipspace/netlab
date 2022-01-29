#
# Create Ansible inventory
#
import typing

import yaml
import os
from box import Box

from .. import common
from . import _TopologyOutput

def node_with_label(f : typing.TextIO, n: Box, settings: Box, indent: typing.Optional[str] = '') -> None:
  f.write('%s  %s [\n' % (indent,n.name))
  f.write('%s    label=<%s [%s]<br /><sub>%s</sub>>\n' % (indent,n.name,n.device,n.loopback.ipv4 or n.loopback.ipv6 or ""))
  f.write('%s    fillcolor="%s"\n' % (indent,settings.colors.get('node','#ff9f01')))
  f.write('%s  ]\n' % indent)

def network_with_label(f : typing.TextIO, n: Box, settings: Box) -> None:
  f.write('  %s [' % n.bridge)
  f.write(' style=filled fillcolor="%s" fontsize=11' % settings.colors.get("stub","#d1bfab"))
  f.write(' label="%s"' % (n.prefix.ipv4 or n.prefix.ipv6 or n.bridge))
  f.write(" ]\n")

def edge_label(f : typing.TextIO, direction: str, data: Box) -> None:
  addr = data.ipv4 or data.ipv6
  if addr:
    f.write(' %slabel="%s"' % (direction,addr))

def edge_p2p(f : typing.TextIO, l: Box, labels: typing.Optional[bool] = False) -> None:
  f.write(' %s -- %s' % (l.left.node, l.right.node))
  f.write(' [')
  if labels:
    edge_label(f,'tail',l[l.left.node])
    edge_label(f,'head',l[l.right.node])
  f.write(' ]\n')

def edge_node_net(f : typing.TextIO, l: Box, k: str, labels: typing.Optional[bool] = False) -> None:
  f.write(" %s -- %s" % (k,l.bridge))
  f.write(' [')
  if labels:
    edge_label(f,'tail',l[k])
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
    f.write('    label="%s (AS %s)"\n' % (label,asn))
  else:
    f.write('    label="AS %s"\n' % asn)

def graph_bgp_clusters(f : typing.TextIO, bgp: Box, settings: Box) -> None:
  for asn in bgp.keys():
    as_start(f,asn,bgp[asn].get('name',None),settings)
    for n in bgp[asn].nodes.values():
      node_with_label(f,n,settings,'  ')
    f.write('  }\n')

def build_maps(topology: Box) -> Box:
  maps = Box({},default_box=True,box_dots=True)
  for name,n in topology.nodes.items():
    maps.nodes[name] = n

  if 'module' in topology and 'bgp' in topology.module:
    for name,n in topology.nodes.items():
      if 'bgp' in n and 'as' in n.bgp:
        maps.bgp[n.bgp['as']].nodes[n.name] = n

  if 'bgp' in topology and 'as_list' in topology.bgp:
    for (asn,asdata) in topology.bgp.as_list.items():
      if 'name' in asdata and asn in maps.bgp:
        maps.bgp[asn].name = asdata.name

  return maps

def graph_topology(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  f = common.open_output_file(fname)
  graph_start(f)

  maps = build_maps(topology)

  if 'bgp' in maps and settings.as_clusters:
    graph_bgp_clusters(f,maps.bgp,settings)
  else:
    for name,n in topology.nodes.items():
      node_with_label(f,n,settings)

  for l in topology.links:
    if l.type == "p2p":
      edge_p2p(f,l,settings.interface_labels)
    else:
      if not l.bridge:
        common.error('Found a lan/stub link without a bridge name, skipping',common.IncorrectValue,'graph')
        next
      network_with_label(f,l,settings)
      for ifdata in l.interfaces:
        if ifdata.node in maps.nodes:
          edge_node_net(f,l,ifdata.node,settings.interface_labels)

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

  f.write("  %s -- %s" % (node.name,session.name))
  f.write('  [\n')
  if session.type == 'ibgp':
    f.write('    color="%s"\n' % settings.colors.get('ibgp','#613913'))
  else:
    f.write('    color="%s"\n' % settings.colors.get('ebgp','#b21a1a'))
  f.write(f'    penwidth=2.5 arrowsize=0.7 dir={arrow_dir}\n')
  f.write('  ]\n')

def graph_bgp(topology: Box, fname: str, settings: Box,g_format: typing.Optional[list]) -> bool:
  if not 'bgp' in topology.get('module',{}):
    common.error('BGP graph format can only be used to draw topologies using BGP')
    return False

  f = common.open_output_file(fname)
  graph_start(f)

  rr_session = g_format is not None and len(g_format) > 1 and g_format[1] == 'rr'

  maps = build_maps(topology)
  graph_bgp_clusters(f,maps.bgp,settings)

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

  def write(self, topology: Box) -> None:
    graphfile = self.settings.filename or 'graph.dot'
    output_format = 'topology'

    if hasattr(self,'filenames'):
      graphfile = self.filenames[0]
      if len(self.filenames) > 1:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[1:]),common.IncorrectValue,'graph')

    if self.format:
      output_format = self.format[0]

    if output_format in graph_dispatch:
      if graph_dispatch[output_format](topology,graphfile,self.settings,self.format):
        print("Created graph file %s in %s format" % (graphfile, output_format))
    else:
      formats = ', '.join(graph_dispatch.keys())
      common.error('Unknown graph format, use one of %s' % formats,common.IncorrectValue,'graph')
