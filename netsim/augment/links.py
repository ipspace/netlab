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
  link_list: list = []

  if not(links):
    return link_list
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

  for af in ('ipv4','ipv6'):
    if af in ifdata and not ifdata[af]:
      del ifdata[af]

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

#
# get_node_link_address: calculate on-link address for the specified node
#
# node: node data collected so far
# ifaddr: interface data collected so far
# node_link_data: existing node-on-link data
# prefix: link prefix (ipv4, ipv6, unnumbered)
# node_id: desired address within the subnet
#

def get_node_link_address(node: Box, ifdata: Box, node_link_data: dict, prefix: dict, node_id: int) -> typing.Optional[str]:
  if common.DEBUG:
    print(f"get_node_link_address for {node.name}:\n"+
          f".. ifdata: {ifdata}\n"+
          f".. node_link_data: {node_link_data}\n"+
          f".. prefix: {prefix}\n"+
          f".. node_id: {node_id}")
  if 'unnumbered' in prefix:          # Special case: old-style unnumbered link
    if common.DEBUG:
      print(f"... node loopback: {node.loopback}")
    for af in ('ipv4','ipv6'):        # Set AF to True for all address families
      if af in node_link_data:
        return(f'{af} address ignored for node {node.name} on a fully-unnumbered link')
      if af in node.loopback:         # ... present on node loopback interface
        ifdata[af] = True
        node_link_data[af] = True
    return None

  for af in ('ipv4','ipv6'):
    node_addr = None
    if af in node_link_data:                  # static IP address or host index
      if isinstance(node_link_data[af],bool): # unnumbered node, leave it alone
        continue
      if isinstance(node_link_data[af],int):  # host portion of IP address specified as an integer
        if af in prefix:
          if isinstance(prefix[af],bool):
            return(f'Node {node.name} is using host index for {af} on an unnumbered link')
          try:
            node_addr = netaddr.IPNetwork(prefix[af][node_link_data[af]])
            node_addr.prefixlen = prefix[af].prefixlen
          except Exception as ex:
            return(
              f'Cannot assign host index {node_link_data[af]} in {af} from prefix {prefix[af]} to node {node.name}\n'+
              f'... {ex}')
        else:
          return(f'Node {node.name} is using host index {node_link_data[af]} for {af} on a link that does not have {af} prefix')
      else:                                  # static IP address
        try:
          node_addr = netaddr.IPNetwork(node_link_data[af])
        except:
          return(f'Invalid {af} link address {node_link_data[af]} for node {node.name}')
        if '/' not in node_link_data[af] and af in prefix:
          node_addr.prefixlen = prefix[af].prefixlen
        if str(node_addr) == str(node_addr.cidr):        # Check whether the node address includes a host portion
          lb = not(':' in str(node_addr)) \
                 and node_addr.prefixlen == 32           # Exception#1: IPv4/32
          lb = lb or node_addr.prefixlen == 128          # Exception#2: IPv6/128
          if not lb:
            return(f'Static node address {node_link_data[af]} for node {node.name} does not include a host portion')
    elif af in prefix: 
      if isinstance(prefix[af],bool):        # New-style unnumbered link
        if prefix[af]:                       # Copy only True value into interface data
          ifdata[af] = prefix[af]            # ... to ensure AF presence in ifdata indicates protocol-on-interface
          node_link_data[af] = prefix[af]
      else:
        try:
          node_addr = netaddr.IPNetwork(prefix[af][node_id])
        except Exception as ex:
          return(
            f'Cannot assign {af} address from prefix {prefix[af]} to node {node.name} with ID {node.id}\n'+
            f'... {ex}')
        node_addr.prefixlen = prefix[af].prefixlen

    if node_addr:
      node_link_data[af] = str(node_addr)
      ifdata[af] = node_link_data[af]

  if common.DEBUG:
    print(f"get_node_link_address for {node.name} completed:\n"+
          f".. ifdata: {ifdata}\n"+
          f".. node_link_data: {node_link_data}")
    print
  return None

def augment_link_prefix(link: Box,pools: typing.List[str],addr_pools: Box) -> dict:
  if 'role' in link:
    pools = [ link.get('role') ] + pools
  if 'prefix' in link:
    pfx_list = addressing.parse_prefix(link.prefix)
  elif 'unnumbered' in link:
    pfx_list = Box({ 'unnumbered': True })
  else:
    pfx_list = addressing.get(addr_pools,pools)
    link.prefix = {
        af: pfx_list[af] if isinstance(pfx_list[af],bool) else str(pfx_list[af])
              for af in ('ipv4','ipv6') if af in pfx_list
      }
    if not link.prefix:
      link.pop('prefix',None)
    if pfx_list.get('unnumbered',None):
      link.unnumbered = True

  return pfx_list

def augment_lan_link(link: Box, addr_pools: Box, ndict: dict, defaults: Box) -> None:
  link_attr_base = get_link_base_attributes(defaults)
  pfx_list = augment_link_prefix(link,['lan'],addr_pools)
  interfaces = {}

  if common.DEBUG:
    print(f'Process LAN link {link}\n... pfx_list {pfx_list}')
  for (node,value) in link.items():
    if node in ndict:
      ifaddr = Box({},default_box=True)
      if value is None:
        value = Box({},default_box=True)

      if not isinstance(value,dict):
        common.error(f'Attributes for node {node} on link {link} must be a dictionary',common.IncorrectValue,'links')
        continue

      errmsg = get_node_link_address(
        node=ndict[node],
        ifdata=ifaddr,
        node_link_data=value,
        prefix=pfx_list,
        node_id=ndict[node].id)
      if errmsg:
        common.error(
          f'{errmsg}\n'+
          common.extra_data_printout(f'link data: {link}'),common.IncorrectValue,'links')

      ifaddr_add_module(ifaddr,link,defaults.get('module'))

      ifaddr = ifaddr + value
      link[node] = value

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
  if not defaults:      # pragma: no cover (almost impossible to get there)
    defaults = Box({})
  pfx_list = augment_link_prefix(link,['p2p','lan'],addr_pools)

  end_names = ['left','right']
  link_nodes: typing.List[Box] = []
  interfaces = []

  for (node,value) in sorted(link.items()):
    if node in ndict:
      ecount = len(link_nodes)
      ifaddr = Box({},default_box=True)
      if link.get('unnumbered',None):
        ifaddr.unnumbered = True
      if value is None:
        value = Box({},default_box=True)

      if not isinstance(value,dict):
        common.error(f'Attributes for node {node} on link {link} must be a dictionary',common.IncorrectValue,'links')
        return None

      errmsg = get_node_link_address(
        node=ndict[node],
        ifdata=ifaddr,
        node_link_data=value,
        prefix=pfx_list,
        node_id=ecount+1)
      if errmsg:
        common.error(
          f'{errmsg}\n'+
          common.extra_data_printout(f'link data: {link}'),common.IncorrectValue,'links')

      ifaddr_add_module(ifaddr,link,defaults.get('module'))

      ifaddr = ifaddr + value
      link[node] = value
      link_nodes.append(Box({ 'name': node, 'link': value, 'ifaddr': ifaddr }))

  if len(link_nodes) > len(end_names): # pragma: no cover (this error is reported earlier)
    common.fatal(f"Internal error: Too many nodes specified on a P2P link {link}",'links')
    return None

  for i in range(0,len(link_nodes)):
    node = link_nodes[i].name
    ifdata = interface_data(link=link,link_attr=link_attr_base,ifdata=link_nodes[i].ifaddr)
    ifdata.name = link.get("name") or (link_nodes[i].name + " -> " + link_nodes[1-i].name)
    add_node_interface(ndict[node],ifdata,defaults)
    interfaces.append(ifdata)

  if not 'name' in link:
    link.name = link_nodes[0].name + " - " + link_nodes[1].name

  for i in range(0,2):
    if 'bridge' in link:
      interfaces[i].bridge = link.bridge
    else:
      interfaces[i].remote_id = ndict[link_nodes[1-i].name].id
      interfaces[i].remote_ifindex = interfaces[1-i].ifindex

    link[end_names[i]] = { 'node': link_nodes[i]['name'],'ifname': interfaces[i].get('ifname') }

    remote = link_nodes[1-i].name
    interfaces[i]['neighbors'] = { remote : { \
      'ifname' : interfaces[1-i]['ifname'] }}
    for af in ('ipv4','ipv6'):
      if af in interfaces[1-i]:
        interfaces[i]['neighbors'][remote][af] = interfaces[1-i][af]
      if af in interfaces[i]:
        link[end_names[i]][af] = interfaces[i][af]

    node = link_nodes[i].name
    ifindex = len(ndict[node].links) - 1
    ndict[node].links[ifindex] = interfaces[i]

  return link

def check_link_attributes(data: Box, nodes: dict, valid: set) -> bool:
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

def get_link_type(data: Box, pools: Box) -> str:
  if data.get('type'):
    return data['type']

  role = data.get('role',None)
  if role:
    pool = pools.get(role,None)
    if pool and pool.get('type'):   # pragma: no cover (not implemented yet, would need attribute propagation in addressing)
      return pool.get('type')

  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  return 'lan' if node_cnt > 2 else 'p2p' if node_cnt == 2 else 'stub'

def check_link_type(data: Box) -> bool:
  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  link_type = data.get('type')

  if not link_type: # pragma: no cover (shouldn't get here)
    common.fatal('Internal error: link type still undefined in check_link_type: %s' % data,'links')
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

def transform(link_list: typing.Optional[Box], defaults: Box, nodes: Box, pools: Box) -> typing.Optional[Box]:
  if not link_list:
    return None

  link_attr_full = get_link_full_attributes(defaults)
  linkindex = defaults.get('link_index',1)

  for link in link_list:
    if not check_link_attributes(data=link,nodes=nodes,valid=link_attr_full):
      continue

    # JvB include node_count in link attributes
    link['node_count'] = link_node_count(link,nodes)

    link['type'] = get_link_type(data=link,pools=pools)
    if not check_link_type(data=link):
      continue

    link.linkindex = linkindex
    if link.type == 'p2p':
      augment_p2p_link(link,pools,nodes,defaults=defaults)
    else:
      if not 'bridge' in link:
        link['bridge'] = "%s_%d" % (defaults.name,linkindex)
      augment_lan_link(link,pools,nodes,defaults=defaults)

    linkindex = linkindex + 1
  return link_list
