#
# Build full-blown topology data model from high-level topology
#

import netaddr
import common
import addressing
import os

link_attr_base = [ 'bridge','type','linkindex' ]
link_attr_full = [ 'prefix' ]

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

def add_node_interface(node,ifdata,defaults={}):
  node_links = node.get('links',[])
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

def interface_data(link,link_attr=[],ifdata={}):
  for k in link_attr:
    if k in link:
      ifdata[k] = link[k]

  return ifdata

def augment_lan_link(link,addr_pools,ndict,defaults={}):
  if 'prefix' in link:
    pfx_list = addressing.parse_prefix(link['prefix'])
  else:
    pfx_list = addressing.get(addr_pools,['lan'])
    link['prefix'] = { af: str(pfx_list[af]) for af in pfx_list }

  interfaces = {}

  for (node,value) in link.items():
    if node in ndict:
      ifaddr = {}
      if value is None:
        value = {}

      for af,pfx in pfx_list.items():
        ip = netaddr.IPNetwork(pfx[ndict[node]['id']])
        ip.prefixlen = pfx.prefixlen
        value[af] = str(ip)
        ifaddr[af] = value[af]

      link[node] = value

      ifdata = interface_data(link=link,link_attr=link_attr_base,ifdata=ifaddr)
      interfaces[node] = add_node_interface(ndict[node],ifdata,defaults)

  for node in interfaces.keys():
    interfaces[node]['neighbors'] = {}
    for remote in interfaces.keys():
      if remote != node:
        interfaces[node]['neighbors'][remote] = { \
          'ifname': interfaces[remote]['ifname'] }
        for af in ('ipv4','ipv6'):
          if af in interfaces[remote]:
            interfaces[node]['neighbors'][remote][af] = interfaces[remote][af]

def augment_p2p_link(link,addr_pools,ndict,defaults={}):
  if 'prefix' in link:
    pfx_list = addressing.parse_prefix(link['prefix'])
  else:
    pfx_list = addressing.get(addr_pools,['p2p','lan'])
    link['prefix'] = { af: str(pfx_list[af]) for af in pfx_list }

  end_names = ['left','right']
  nodes = []
  interfaces = []

  for (node,value) in sorted(link.items()):
    if node in ndict:
      ecount = len(nodes)
      ifaddr = {}
      if value is None:
        value = {}

      for af,pfx in pfx_list.items():
        ip = netaddr.IPNetwork(pfx[ecount+1])
        ip.prefixlen = pfx.prefixlen
        value[af] = str(ip)
        ifaddr[af] = value[af]

      link[node] = value
      nodes.append({ 'name': node, 'link': value, 'ifaddr': ifaddr })

  if len(nodes) > len(end_names):
    print("Too many nodes specified on a P2P link")
    return

  for i in range(0,len(nodes)):
    node = nodes[i]['name']
    ifdata = interface_data(link=link,link_attr=link_attr_base,ifdata=nodes[i]['ifaddr'])
    interfaces.append(add_node_interface(ndict[node],ifdata,defaults))

  for i in range(0,2):
    if 'bridge' in link:
      interfaces[i]['bridge'] = link['bridge']
    else:
      interfaces[i]['remote_id'] = ndict[nodes[1-i]['name']]['id']
      interfaces[i]['remote_ifindex'] = interfaces[1-i]['ifindex']

    link[end_names[i]] = { 'node': nodes[i]['name'],'ifname': interfaces[i].get('ifname') }

    remote = nodes[1-i]['name']
    interfaces[i]['neighbors'] = { remote : { \
      'ifname' : interfaces[1-i]['ifname'] }}
    for af in ('ipv4','ipv6'):
      if af in interfaces[1-i]:
        interfaces[i]['neighbors'][remote][af] = interfaces[1-i][af]
      if af in interfaces[i]:
        link[end_names[i]][af] = interfaces[i][af]

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

def transform(link_list,defaults,ndict,pools):
  if not link_list:
    return

  link_attr_base.extend(defaults.get('link_attr',[]))
  link_attr_full.extend(link_attr_base)

  linkindex = defaults.get('link_index',1)

  for link in link_list:
    if not check_link_attributes(data=link,nodes=ndict,valid=link_attr_full):
      continue

    if not link.get('type'):
      link['type'] = get_link_type(data=link,nodes=ndict)

    if not check_link_type(data=link,nodes=ndict):
      continue

    link['linkindex'] = linkindex
    if link['type'] == 'p2p':
      augment_p2p_link(link,pools,ndict,defaults=defaults)
    else:
      if not 'bridge' in link:
        link['bridge'] = "%s_%d" % (defaults['name'],linkindex)
      augment_lan_link(link,pools,ndict,defaults=defaults)

    linkindex = linkindex + 1
  return link_list
