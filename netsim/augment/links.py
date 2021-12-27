#
# Create detailed link data structures including automatic interface numbering
# from high-level topology
#
import typing

import netaddr
from box import Box

# Related modules
from .. import common
from .. import addressing

def get_link_full_attributes(defaults: Box) -> set:
  attributes = defaults.get('attributes',{})
  user = attributes.get('link',[])
  internal = attributes.get('link_internal',[])

  set_attributes = set(user).union(set(internal))
  if 'module' in defaults:
    set_attributes = set_attributes.union(set(defaults.module))

  if 'link_attr' in defaults:
    set_attributes = set_attributes.union(set(defaults.link_attr))

  return set_attributes

def get_link_base_attributes(defaults: Box) -> set:
  attributes = defaults.get('attributes',{})
  no_propagate = attributes.get('link_no_propagate')
  return get_link_full_attributes(defaults) - set(no_propagate)

def adjust_link_list(links: typing.Optional[typing.List[typing.Any]]) -> typing.Optional[typing.List[typing.Dict]]:
  link_list = []

  if not(links):
    return None                  # pragma: no cover (this is a sanity-check safeguard)
  for l in links:
    if isinstance(l,dict):
      link_list.append(l)
    elif isinstance(l,list):
      link_list.append({ key: None for key in l })
    else:
      link_list.append({ key: None for key in l.split('-') })
  return link_list

def add_node_interface(node: Box, ifdata: Box, defaults: Box) -> int:
  if not 'links' in node:
    node.links = []

  ifindex_offset = defaults.devices[node.device].get('ifindex_offset',1)
  ifindex = len(node.links) + ifindex_offset

  ifname_format = defaults.devices[node.device].interface_name

  ifdata.ifindex = ifindex
  if ifname_format:
    ifdata.ifname = ifname_format % ifindex

  if "provider_interface_name" in defaults.devices[node.device]:
    ifdata.provider_ifname = defaults.devices[node.device].provider_interface_name % ifindex

  node.links.append(ifdata)
  return len(node.links)

# Add common interface data to node ifaddr structure
#
def interface_data(link: Box, link_attr: set, ifdata: Box) -> Box:
  for k in link_attr:
    if k in link:
      if not k in ifdata:
        ifdata[k] = link[k]
      elif isinstance(link[k],dict) and isinstance(ifdata[k],dict):
        ifdata[k] = link[k] + ifdata[k]
  return ifdata

#
# Add module-specific data to node ifaddr structure
#
# Iterate over modules, for every matching key in link definition
# copy the value into node ifaddr
#
def ifaddr_add_module(ifaddr: Box, link: Box, module: Box) -> None:
  if module:
    for m in module:
      if m in link:
        ifaddr[m] = link[m]

def augment_lan_link(link: Box, addr_pools: Box, ndict: dict, defaults: Box) -> None:
  link_attr_base = get_link_base_attributes(defaults)
  if 'prefix' in link:
    pfx_list = addressing.parse_prefix(link.prefix)
  else:
    pfx_list = addressing.get(addr_pools,[link.get('role'),'lan'])
    link.prefix = { af: str(pfx_list[af]) for af in pfx_list }

  interfaces = {}

  for (node,value) in link.items():
    if node in ndict:
      ifaddr = Box({},default_box=True)
      if value is None:
        value = Box({},default_box=True)

      if not isinstance(value,dict):
        common.error(f'Attributes for node {node} on link {link} must be a dictionary',common.IncorrectValue,'links')
        continue
      for af,pfx in pfx_list.items():
        if not value[af]:
          ip = netaddr.IPNetwork(pfx[ndict[node].id])
        else:
          try:
            ip = netaddr.IPNetwork(value[af])
          except:
            common.error('Invalid %s link address for node %s: %s' % (af,node,value[af]),common.IncorrectValue,'links')
            continue

        if ip.first == ip.last:
          ip.prefixlen = pfx.prefixlen
        value[af] = str(ip)
        ifaddr[af] = value[af]

      link[node] = value
      ifaddr_add_module(ifaddr,link,defaults.get('module'))
      ifaddr = ifaddr + value

      if link.type != "stub":
        n_list = filter(lambda n: n in ndict and n != node,link.keys())
        ifaddr.name = link.get("name") or (node + " -> [" + ",".join(list(n_list))+"]")

      interfaces[node] = interface_data(link=link,link_attr=link_attr_base,ifdata=ifaddr)
      add_node_interface(ndict[node],interfaces[node],defaults)

  for node in interfaces.keys():
    interfaces[node].neighbors = {}
    for remote in interfaces.keys():
      if remote != node:
        interfaces[node].neighbors[remote] = { \
          'ifname': interfaces[remote]['ifname'] }
        for af in ('ipv4','ipv6'):
          if af in interfaces[remote]:
            interfaces[node].neighbors[remote][af] = interfaces[remote][af]
    ifindex = len(ndict[node].links) - 1
    ndict[node].links[ifindex] = interfaces[node]

def augment_p2p_link(link: Box, addr_pools: Box, ndict: dict, defaults: Box) -> typing.Optional[Box]:
  link_attr_base = get_link_base_attributes(defaults)
  if not defaults:
    defaults = Box({})
  if 'prefix' in link:
    pfx_list = addressing.parse_prefix(link.prefix)
  else:
    pool = addressing.get_pool(addr_pools,[link.get('role'),'p2p','lan'])
    if pool is None:
      common.error("Cannot get addressing pool for P2P link: %s" % str(link),common.MissingValue,'links')
      return None

    pfx_list = addressing.get_pool_prefix(addr_pools,pool)
    link.prefix = { af: str(pfx_list[af]) for af in pfx_list }
    if pool and addr_pools[pool].get('unnumbered',None):
      link.unnumbered = True

  end_names = ['left','right']
  nodes: typing.List[Box] = []
  interfaces = []

  for (node,value) in sorted(link.items()):
    if node in ndict:
      ecount = len(nodes)
      ifaddr = Box({},default_box=True)
      if link.get('unnumbered',None):
        ifaddr.unnumbered = True
      if value is None:
        value = Box({},default_box=True)

      if not isinstance(value,dict):
        common.error(f'Attributes for node {node} on link {link} must be a dictionary',common.IncorrectValue,'links')
        continue

      for af,pfx in pfx_list.items():
        ip = netaddr.IPNetwork(pfx[ecount+1])
        ip.prefixlen = pfx.prefixlen
        value[af] = str(ip)
        ifaddr[af] = value[af]

      ifaddr_add_module(ifaddr,link,defaults.get('module'))
      ifaddr = ifaddr + value
      link[node] = value
      nodes.append(Box({ 'name': node, 'link': value, 'ifaddr': ifaddr }))

  if len(nodes) > len(end_names):
    common.error("Too many nodes specified on a P2P link",common.IncorrectValue,'links')
    return None

  for i in range(0,len(nodes)):
    node = nodes[i].name
    ifdata = interface_data(link=link,link_attr=link_attr_base,ifdata=nodes[i].ifaddr)
    ifdata.name = link.get("name") or (nodes[i].name + " -> " + nodes[1-i].name)
    add_node_interface(ndict[node],ifdata,defaults)
    interfaces.append(ifdata)

  if not 'name' in link:
    link.name = nodes[0].name + " - " + nodes[1].name

  for i in range(0,2):
    if 'bridge' in link:
      interfaces[i].bridge = link.bridge
    else:
      interfaces[i].remote_id = ndict[nodes[1-i].name].id
      interfaces[i].remote_ifindex = interfaces[1-i].ifindex

    link[end_names[i]] = { 'node': nodes[i]['name'],'ifname': interfaces[i].get('ifname') }

    remote = nodes[1-i].name
    interfaces[i]['neighbors'] = { remote : { \
      'ifname' : interfaces[1-i]['ifname'] }}
    for af in ('ipv4','ipv6'):
      if af in interfaces[1-i]:
        interfaces[i]['neighbors'][remote][af] = interfaces[1-i][af]
      if af in interfaces[i]:
        link[end_names[i]][af] = interfaces[i][af]

    node = nodes[i].name
    ifindex = len(ndict[node].links) - 1
    ndict[node].links[ifindex] = interfaces[i]

  return link

def check_link_attributes(data: Box, nodes: dict, valid: set) -> bool:
  nodes = nodes or {}
  ok = True
  for k in data.keys():
    if k not in nodes and k not in valid:
      common.error("Invalid link attributes '%s' in %s" % (k,data),common.IncorrectValue,'links')
      ok = False

  return ok

def link_node_count(data: Box, nodes: dict) -> int:
  node_cnt = 0
  for k in data.keys():
    if k in nodes:
      node_cnt = node_cnt + 1
  return node_cnt

def get_link_type(data: Box, nodes: dict, pools: Box) -> str:
  if data.get('type'):
    return data['type']

  role = data.get('role',None)
  if role:
    pool = pools.get(role,None)
    if pool and pool.get('type'):
      return pool.get('type')

  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  return 'lan' if node_cnt > 2 else 'p2p' if node_cnt == 2 else 'stub'

def check_link_type(data: Box, nodes: dict) -> bool:
  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  link_type = data.get('type')

  if not link_type:
    common.fatal('Link type still undefined in check_link_type: %s' % data,'links')
    return False

  if node_cnt == 0:
    common.error('No valid nodes on link %s' % data,common.MissingValue,'links')
    return False

  if link_type == 'stub' and node_cnt > 1:
    common.error('More than one node connected to a stub link: %s' % data,common.IncorrectValue,'links')
    return False

  if link_type == 'p2p' and node_cnt != 2:
    common.error('Point-to-point link needs exactly two nodes: %s' % data,common.IncorrectValue,'links')
    return False

  if not link_type in [ 'stub','p2p','lan']:
    common.error('Invalid link type %s: %s' % (link_type,data),common.IncorrectValue,'links')
    return False
  return True

def transform(link_list: typing.Optional[Box], defaults: Box, ndict: dict, pools: Box) -> typing.Optional[Box]:
  if not link_list:
    return None

  link_attr_full = get_link_full_attributes(defaults)
  linkindex = defaults.get('link_index',1)

  for link in link_list:
    if not check_link_attributes(data=link,nodes=ndict,valid=link_attr_full):
      continue

    # JvB include node_count in link attributes
    link['node_count'] = link_node_count(link,ndict)

    link['type'] = get_link_type(data=link,nodes=ndict,pools=pools)
    if not check_link_type(data=link,nodes=ndict):
      continue

    link.linkindex = linkindex
    if link.type == 'p2p':
      augment_p2p_link(link,pools,ndict,defaults=defaults)
    else:
      if not 'bridge' in link:
        link['bridge'] = "%s_%d" % (defaults.name,linkindex)
      augment_lan_link(link,pools,ndict,defaults=defaults)

    linkindex = linkindex + 1
  return link_list
