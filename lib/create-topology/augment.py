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

  if not(links):
    return
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

    if not n.get('name'):
      common.error("ERROR: node does not have a name %s" % str(n))
      continue

    for id_param in ['mgmt_mac','mgmt_ip','loopback']:
      if id_param in defaults:
        n[id_param] = defaults[id_param] % id

    if not 'device' in n:
      n['device'] = defaults.get('device')

    device_data = common.get_value( \
                data=defaults,
                path=['devices',n['device']])
    if not device_data:
      common.error("ERROR: Unsupported device type %s: %s" % (n['device'],n))
      continue

    mgmt_if = device_data.get('mgmt_if')
    if not mgmt_if:
      ifname_format = device_data.get('interface_name')
      if not ifname_format:
        common.fatal("FATAL: Missing interface name template for device type %s" % n['device'])

      ifindex_offset = device_data.get('ifindex_offset',1)
      mgmt_if = ifname_format % (ifindex_offset - 1)
    n['mgmt_if'] = mgmt_if

    if 'box' in device_data:
      n['box'] = device_data['box']

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

link_attr_list = [ 'bridge','type','prefix' ]

def interface_data(link,link_attr=[],ifdata={}):
  for k in link_attr:
    if k in link:
      ifdata[k] = link[k]

  return ifdata

def augment_lan_link(link,pfx_list,ndict,defaults={}):
  if 'prefix' in link:
    pfx = netaddr.IPNetwork(link['prefix'])
  else:
    pfx = next(pfx_list)
    link['prefix'] = str(pfx)

  interfaces = {}

  link_attr = ['bridge','type']
  link_attr.extend(defaults.get('link_attr',[]))

  for (node,value) in link.items():
    if node in ndict:
      if value is None:
        value = {}
      ip = netaddr.IPNetwork(pfx[ndict[node]['id']])
      ip.prefixlen = pfx.prefixlen
      value['ip'] = str(ip)
      link[node] = value

      ifdata = interface_data(link=link,link_attr=link_attr,ifdata={ 'ip': link[node]['ip'] })
      interfaces[node] = add_node_interface(ndict[node],ifdata,defaults)

  for node in interfaces.keys():
    interfaces[node]['neighbors'] = {}
    for remote in interfaces.keys():
      if remote != node:
        interfaces[node]['neighbors'][remote] = { \
          'ip': interfaces[remote]['ip'], \
          'ifname': interfaces[remote]['ifname'] }

def augment_p2p_link(link,pfx_list,ndict,defaults={}):
  if 'prefix' in link:
    pfx = netaddr.IPNetwork(link['prefix'])
  else:
    pfx = next(pfx_list)
    link['prefix'] = str(pfx)

  end_names = ['left','right']
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

  if len(nodes) > len(end_names):
    print("Too many nodes specified on a P2P link")
    return

  link_attr = ['bridge','type']
  link_attr.extend(defaults.get('link_attr',[]))

  for i in range(0,len(nodes)):
    node = nodes[i]['name']
    ifdata = interface_data(link=link,link_attr=link_attr,ifdata={ 'ip': link[node]['ip'] })
    interfaces.append(add_node_interface(ndict[node],ifdata,defaults))

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

def check_link_attributes(data,nodes={},valid=[]):
  ok = True
  for k in data.keys():
    if k not in nodes and k not in valid:
      common.error("Invalid link attributes '%s' in %s" % (k,data))
      ok = False

  return ok

def link_node_count(data,nodes):
  node_cnt = 0
  for k in data.keys():
    if k in nodes:
      node_cnt = node_cnt + 1
  return node_cnt

def get_link_type(data,nodes):
  if data.get('type'):
    return data['type']

  node_cnt = link_node_count(data,nodes)
  return 'lan' if node_cnt > 2 else 'p2p' if node_cnt == 2 else 'stub'

def check_link_type(data,nodes):
  node_cnt = link_node_count(data,nodes)
  link_type = data.get('type')

  if not link_type:
    common.fatal('Link type still undefined in check_link_type: %s' % data)
    return False

  if node_cnt == 0:
    common.error('No valid nodes on link %s' % data)
    return False

  if link_type == 'stub' and node_cnt > 1:
    common.error('More than one node connected to a stub link: %s' % data)
    return False

  if link_type == 'p2p' and node_cnt != 2:
    common.error('Point-to-point link needs exactly two nodes: %s' % data)
    return False

  if not link_type in [ 'stub','p2p','lan']:
    common.error('Invalid link type %s: %s' % (link_type,data))
    return False
  return True

def augment_links(link_list,defaults,ndict):
  if not link_list:
    return

  lan_pfx   = defaults.get('lan','10.0.0.0/16')
  lan_subnet= defaults.get('lan_subnet',24)
  p2p_pfx   = defaults.get('p2p','10.1.0.0/16')
  p2p_subnet= defaults.get('p2p_subnet',30)
  lan_list  = netaddr.IPNetwork(lan_pfx).subnet(lan_subnet)
  p2p_list  = netaddr.IPNetwork(p2p_pfx).subnet(p2p_subnet)

  link_attr_list.extend(defaults.get('link_attr',[]))
  linkindex = defaults.get('link_index',1)

  for link in link_list:
    if not check_link_attributes(data=link,nodes=ndict,valid=link_attr_list):
      continue

    if not link.get('type'):
      link['type'] = get_link_type(data=link,nodes=ndict)

    if not check_link_type(data=link,nodes=ndict):
      continue

    link['index'] = linkindex
    if link['type'] == 'p2p':
      augment_p2p_link(link,p2p_list,ndict,defaults=defaults)
    else:
      if not 'bridge' in link:
        link['bridge'] = "%s_%d" % (defaults['name'],linkindex)
      augment_lan_link(link,lan_list,ndict,defaults=defaults)

    linkindex = linkindex + 1
  return link_list

def augment(topology):
  check_required_elements(topology)
  topology['nodes'] = adjust_node_list(topology['nodes'])
  common.exit_on_error()
  topology['links'] = adjust_link_list(topology['links'])
  common.exit_on_error()

  ndict = augment_nodes(topology,topology.get('defaults',{}))
  common.exit_on_error()
  augment_links(topology['links'],topology.get('defaults',{}),ndict)
  common.exit_on_error()
