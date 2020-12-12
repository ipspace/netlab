#
# Build full-blown topology data model from high-level topology
#

import netaddr
import common
import os

def check_required_elements(topology):
  for rq in ['nodes','links','defaults']:
    if not rq in topology:
      common.error("Topology error: missing '%s' element" % rq)

  if not 'name' in topology:
    topo_name = os.path.basename(os.path.dirname(os.path.realpath(topology['input'][0])))
    topology['name'] = topo_name

  topology['defaults']['name'] = topology['name']

def adjust_node_list(nodes):
  node_list = []
  for n in nodes:
    node_list.append(n if type(n) is dict else { 'name': n})
  return node_list

def adjust_link_list(links):
  link_list = []
  for l in links:
    if type(l) is dict:
      link_list.append(l)
    elif type(l) is list:
      link_list.append({ key: None for key in l })
    else:
      link_list.append({ key: None for key in l.split('-') })
  return link_list

def augment_nodes(topology,defaults):
  id = 0

  ndict = {}
  for n in topology['nodes']:
    id = id + 1
    n['id'] = id
    if not 'device' in n:
      n['device'] = defaults.get('device')
      if not n['device'] in defaults.get('devices'):
        print("WARNING: Unsupported device type %s" % n['device'])
    if 'mac' in defaults:
      n['mgmt_mac'] = defaults['mac'] % id

    if 'mgmt' in defaults:
      n['mgmt_ip'] = defaults['mgmt'] % id

    if 'loopback' in defaults:
      n['loopback'] = defaults['loopback'] % id

    mgmt_if = common.get_value( \
                data=defaults,
                path=['devices',n['device'],'mgmt_if'])
    if not mgmt_if:
      ifname_format = common.get_value( \
                data=defaults,
                path=['devices',n['device'],'interface_name'])
      ifindex_offset = common.get_value( \
                data=defaults,
                path=['devices',n['device'],'ifindex_offset'], \
                default=1)
      mgmt_if = ifname_format % (ifindex_offset - 1)
    n['mgmt_if'] = mgmt_if

    if not n.get('name'):
      common.error("ERROR: node does not have a name %s" % str(n))
      return

    ndict[n['name']] = n

  topology['nodes_map'] = ndict
  return ndict

def add_node_interface(node,ifdata,defaults={}):
  node_links = node.get('links')
  if node_links is None:
    node_links = []

  ifindex_offset = common.get_value( \
                     data=defaults, \
                     path=['devices',node['device'],'ifindex_offset'], \
                     default=1)
  ifindex = len(node_links) + ifindex_offset

  ifname_format = common.get_value( \
                    data=defaults,
                    path=['devices',node['device'],'interface_name'], \
                    default=None)

  ifdata['ifindex'] = ifindex
  if ifname_format is not None:
    ifdata['ifname'] = ifname_format % ifindex

  node_links.append(ifdata)
  node['links'] = node_links
  return ifdata

def augment_bridge_link(link,pfx_list,ndict,**kwargs):
  pfx = next(pfx_list)
  link['prefix'] = str(pfx)

  interfaces = {}

  for (node,value) in link.items():
    if node in ndict:
      if value is None:
        value = {}
      ip = netaddr.IPNetwork(pfx[ndict[node]['id']])
      ip.prefixlen = pfx.prefixlen
      value['ip'] = str(ip)
      link[node] = value

      interfaces[node] = add_node_interface(ndict[node], \
         { 'ip' : value['ip'], 'bridge': link['bridge'] }, \
         defaults=kwargs.get('defaults'))

    elif not node in ['bridge','prefix','type']:
      print("Unknown LAN link attribute '%s': %s" % (node,str(link)))

  for node in interfaces.keys():
    interfaces[node]['neighbors'] = {}
    for remote in interfaces.keys():
      if remote != node:
        interfaces[node]['neighbors'][remote] = { \
          'ip': interfaces[remote]['ip'], \
          'ifname': interfaces[remote]['ifname'] }

def augment_p2p_link(link,pfx_list,ndict,**kwargs):
  end_names = ['left','right']

  pfx = next(pfx_list)
  link['prefix'] = str(pfx)
  augment = {}
  nodes = []
  interfaces = []

  for (node,value) in link.items():
    if node in ndict:
      ecount = len(nodes)
      if value is None:
        value = {}
      ip = netaddr.IPNetwork(pfx[ecount+1])
      ip.prefixlen = pfx.prefixlen
      value['ip'] = str(ip)
      link[node] = value
      nodes.append({ 'name': node, 'link': value })
    elif not node in ['type','prefix','bridge']:
      print("Unknown P2P link attribute '%s': %s" % (node,str(link)))

  if len(nodes) > len(end_names):
    print("Too many nodes specified on a P2P link")
    return

  for i in range(0,len(nodes)):
    node = nodes[i]['name']
    interfaces.append(add_node_interface(ndict[node],{ 'ip': link[node]['ip'] },defaults=kwargs.get('defaults')))

  for i in range(0,2):
    if 'bridge' in link:
      interfaces[i]['bridge'] = link['bridge']
    else:
      interfaces[i]['remote_id'] = ndict[nodes[1-i]['name']]['id']
      interfaces[i]['remote_ifindex'] = interfaces[1-i]['ifindex']
    interfaces[i]['neighbors'] = { nodes[1-i]['name'] : { \
      'ifname' : interfaces[1-i]['ifname'], \
      'ip': interfaces[1-i]['ip'] }}

  for i in range(0,2):
    link[end_names[i]] = { 'node': nodes[i]['name'], 'ip': interfaces[i]['ip'], 'ifname': interfaces[i].get('ifname') }

  return link

def augment_links(link_list,defaults,ndict):
  lan_pfx   = defaults.get('lan','10.0.0.0/16')
  lan_subnet= defaults.get('lan_subnet',24)
  p2p_pfx   = defaults.get('p2p','10.1.0.0/16')
  p2p_subnet= defaults.get('p2p_subnet',30)
  lan_list  = netaddr.IPNetwork(lan_pfx).subnet(lan_subnet)
  p2p_list  = netaddr.IPNetwork(p2p_pfx).subnet(p2p_subnet)

  for link in link_list:
    # multi-access links have bridge names
    if 'bridge' in link and link.get('type','') != 'p2p':
      augment_bridge_link(link,lan_list,ndict,defaults=defaults)
    else:
      augment_p2p_link(link,p2p_list,ndict,defaults=defaults)
  return link_list

def augment(topology):
  check_required_elements(topology)
  topology['nodes'] = adjust_node_list(topology['nodes'])
  topology['links'] = adjust_link_list(topology['links'])

  ndict = augment_nodes(topology,topology.get('defaults',{}))
  augment_links(topology['links'],topology.get('defaults',{}),ndict)