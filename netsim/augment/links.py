#
# Create detailed link data structures including automatic interface numbering
# from high-level topology
#
import typing

import netaddr
from box import Box

# Related modules
from .. import common
from .. import data
from .. import addressing
from . import devices

IFATTR: str = 'interfaces'          # Just in case we decide to call it something else not 'interfaces'

def adjust_interface_list(iflist: list, link: typing.Any, nodes: Box) -> list:
  link_intf = []
  for n in iflist:                      # Sanity check of interface data
    if isinstance(n,str):               # Another shortcut: node name as string
      n = Box({ 'node': n },default_box=True,box_dots=True)
    if not isinstance(n,dict):          # Still facing non-dict data type?
      common.error(                     # ... report an error
        f'Interface description {n} on link {link} must be a dictionary',
        common.IncorrectValue,
        'links')
    elif not 'node' in n:               # Do we have node name in interface data?
      common.error(                     # ... no? Too bad, throw an error
        f'Interface data {n} on link {link} is missing a "node" attribute',
        common.MissingValue,
        'links')
    elif not n['node'] in nodes:        # Is the node name valid?
      common.error(                     # ... it's not, get lost
        f'Interface data {n} on link {link} refers to an unknown node {n["node"]}',
        common.IncorrectValue,
        'links')
    else:
      link_intf.append(n)               # Interface data is OK, append it to interface list

  return link_intf

def adjust_link_list(links: list, nodes: Box) -> list:
  global IFATTR
  link_list: list = []

  if not(links):
    return link_list

  link_cnt = 0
  for l in links:
    if isinstance(l,dict) and IFATTR in l:               # a dictionary with 'interfaces' element
      l = Box(l,default_box=True,box_dots=True)
      data.must_be_list(l,IFATTR,f'link[{link_cnt}]')    # ... check it's a list and move on
      l[IFATTR] = adjust_interface_list(l[IFATTR],l,nodes)
      link_list.append(l)
    elif isinstance(l,dict):                             # a dictionary without 'interfaces' element
      link_data = {}                                     # ... split it into link attributes
      link_intf = []                                     # ... and a list of nodes
      for (k,v) in l.items():
        if k in nodes:                                   # Node name -> interface list
          if not v:
            v = Box({},default_box=True,box_dots=True)
          if not isinstance(v,dict):                     # Interface data must be a dictionary
            common.error(
              f'Interface data {v} for node {k} on link {l} must be a dictionary',
              common.IncorrectValue,
              'links')
            continue
          v['node'] = k                                  # ... add 'node' to the interface so we know what node it belongs to
          link_intf.append(v)
        else:
          link_data[k] = v                  # ... otherwise copy key/value pair to link data
      link_data[IFATTR] = link_intf         # Add revised interface data to link data
      link_list.append(link_data)           # ... and move on
    elif isinstance(l,list):
      link_list.append(Box({ IFATTR: adjust_interface_list(l,l,nodes) },default_box=True,box_dots=True))
    else:                                   # Assuming the link value is a string, split
      link_intf = []
      for n in l.split('-'):                # ... split it into a list of nodes
        if n in nodes:                      # If the node name is valid
          link_intf.append({ 'node': n })   # ... append it to the list of interfaces
        else:
          common.error(
            f'Link string {l} refers to an unknown node {n}',
            common.IncorrectValue,
            'links')
      link_list.append({ IFATTR: link_intf })
    link_cnt = link_cnt + 1

  if common.DEBUG:
    print("Adjusted link list")
    print("=" * 60)
    print(common.print_yaml(link_list))

  return link_list

def get_link_full_attributes(defaults: Box, with_modules: bool = True) -> set:
  attributes = defaults.get('attributes',{})
  user = attributes.get('link',[])
  internal = attributes.get('link_internal',[])

  set_attributes = set(user).union(set(internal))
  if 'module' in defaults and with_modules:
    set_attributes = set_attributes.union(set(defaults.module))

  if 'link_attr' in defaults:
    set_attributes = set_attributes.union(set(defaults.link_attr))

  return set_attributes

def get_link_base_attributes(defaults: Box, with_modules: bool = True) -> set:
  attributes = defaults.get('attributes',{})
  no_propagate = attributes.get('link_no_propagate')
  return get_link_full_attributes(defaults,with_modules) - set(no_propagate)

def add_node_interface(node: Box, ifdata: Box, defaults: Box) -> Box:
  ifindex_offset = devices.get_device_attribute(node,'ifindex_offset',defaults)
  if ifindex_offset is None:
    ifindex_offset = 1

  # Allow user to select a specific interface index per link
  ifindex = ifdata.get('ifindex',None) or (len(node.interfaces) + ifindex_offset)

  ifname_format = devices.get_device_attribute(node,'interface_name',defaults)

  ifdata.ifindex = ifindex
  if ifname_format and not 'ifname' in ifdata:
    ifdata.ifname = ifname_format % ifindex

  pdata = devices.get_provider_data(node,defaults).get('interface',{})
  pdata = Box(pdata,box_dots=True,default_box=True)                     # Create a copy of the provider interface data
  if 'name' in pdata:
    pdata.name = pdata.name % ifindex

  if pdata:
    provider = devices.get_provider(node,defaults)
    ifdata[provider] = pdata

  for af in ('ipv4','ipv6'):
    if af in ifdata and not ifdata[af]:
      del ifdata[af]

  if 'mtu' in node:                             # Is node-level MTU defined (node setting, lab default or device default)
    sys_mtu = devices.get_device_features(node,defaults).initial.get('system_mtu',False)
    if 'mtu' in ifdata:                         # Is MTU defined on the interface?
      if sys_mtu and node.mtu == ifdata.mtu:    # .. is it equal to node MTU?
        ifdata.pop('mtu',None)                  # .... remove interface MTU on devices that support system MTU
    else:                                       # Node MTU is defined, interface MTU is not
      if not sys_mtu:                           # .. does the device support system MTU?
        ifdata.mtu = node.mtu                   # .... no, copy node MTU to interface MTU

  node.interfaces.append(ifdata)

  # Box modifies the dict in place, return a reference to be updated
  # return len(node.links)
  return node.interfaces[-1]

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
  if common.DEBUG:     # pragma: no cover (debugging)
    print(f"get_node_link_address for {node.name}:\n"+
          f".. ifdata: {ifdata}\n"+
          f".. node_link_data: {node_link_data}\n"+
          f".. prefix: {prefix}\n"+
          f".. node_id: {node_id}")
  if 'unnumbered' in prefix:          # Special case: old-style unnumbered link
    if common.DEBUG:     # pragma: no cover (debugging)
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
          index = node_id-1 if af == 'ipv4' and prefix[af].prefixlen==31 else node_id
          node_addr = netaddr.IPNetwork(prefix[af][index])
        except Exception as ex:
          return(
            f'Cannot assign {af} address from prefix {prefix[af]} to node {node.name} with ID {node.id}\n'+
            f'... {ex}')
        node_addr.prefixlen = prefix[af].prefixlen

    if node_addr:
      node_link_data[af] = str(node_addr)
      ifdata[af] = node_link_data[af]

  if common.DEBUG:     # pragma: no cover (debugging)
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
    if isinstance(link.prefix,str):
      link.prefix = addressing.rebuild_prefix(pfx_list)
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
  link_attr_nomod = get_link_base_attributes(defaults,False)

  if common.DEBUG:     # pragma: no cover (debugging)
    print(f'\nProcess LAN link {link}')

  pfx_list = augment_link_prefix(link,['lan'],addr_pools)
  interfaces = []

  if common.DEBUG:     # pragma: no cover (debugging)
    print(f'... on-link prefixes: {pfx_list}')

  link_cnt = 0
  for value in link[IFATTR]:
    node = value.node
    ifaddr = Box({},default_box=True)
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

    ifaddr_add_module(ifaddr,link,ndict[node].get('module'))

    ifaddr = ifaddr + value
    ifaddr.pop('node',None)               # Remove the 'node' attribute from interface data -- now we know where it belongs
    link[IFATTR][link_cnt] = value

    if link.type != "stub":
      n_list = [ link[IFATTR][i].node for i in range(0,len(link[IFATTR])) if i != link_cnt ]
      ifaddr.name = link.get("name") or (node + " -> [" + ",".join(list(n_list))+"]")

    ifdata = interface_data(link=link,link_attr=link_attr_nomod,ifdata=ifaddr)
    node_intf = add_node_interface(ndict[node],ifdata,defaults)
    value.ifindex = node_intf.ifindex
    interfaces.append({ 'node': node, 'data':  node_intf })

    link_cnt = link_cnt + 1

  for node_if in interfaces:
    node_if['data'].neighbors = []
    for remote_if in interfaces:
      if remote_if['node'] != node_if['node'] or remote_if['data'].ifindex != node_if['data'].ifindex:
        ngh_data = { 'ifname': remote_if['data'].ifname, 'node': remote_if['node'] }
        for af in ('ipv4','ipv6'):
          if af in remote_if['data']:
            ngh_data[af] = remote_if['data'][af]
        node_if['data'].neighbors.append(ngh_data)

  if common.DEBUG:     # pragma: no cover (debugging)
    print(f'Final LAN link data: {link}\n')

def augment_p2p_link(link: Box, addr_pools: Box, ndict: dict, defaults: Box) -> typing.Optional[Box]:
  link_attr_base = get_link_base_attributes(defaults)
  link_attr_nomod = get_link_base_attributes(defaults,False)

  if not defaults:      # pragma: no cover (almost impossible to get there)
    defaults = Box({})
  if common.DEBUG:     # pragma: no cover (debugging)
    print(f'\nProcess P2P link {link}')
  pfx_list = augment_link_prefix(link,['p2p','lan'],addr_pools)

  end_names = ['left','right']
  link_nodes: typing.List[Box] = []
  interfaces: typing.List[Box] = []

  if len(link[IFATTR]) > len(end_names): # pragma: no cover (this error is reported earlier)
    common.fatal(f"Internal error: Too many nodes specified on a P2P link {link}",'links')
    return None

  link[IFATTR] = sorted(link[IFATTR],key=lambda v: v.node)       # Keep nodes sorted in alphabetic order for historic reasons
  value: Box
  for intf_cnt,value in enumerate(link[IFATTR]):
    node = value.node
    ecount = len(link_nodes)
    ifaddr = Box({},default_box=True,box_dots=True)
    if link.get('unnumbered',None):
      ifaddr.unnumbered = True

    if not isinstance(value,dict):        # pragma: no cover -- caught earlier in adjust_interface_list
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

    ifaddr_add_module(ifaddr,link,ndict[node].get('module'))

    ifaddr = ifaddr + value
    ifaddr.pop('node',None)               # Remove the 'node' attribute from interface data -- now we know where it belongs
#    link[IFATTR][intf_cnt] = value
    link_nodes.append(Box({ 'name': node, 'link': value, 'ifaddr': ifaddr }))

    ifdata = interface_data(link=link,link_attr=link_attr_nomod,ifdata=ifaddr)
    if 'bridge' in link:
      ifdata.bridge = link.bridge
    ifdata.name = link.get("name") or (link[IFATTR][intf_cnt].node + " -> " + link[IFATTR][1-intf_cnt].node)
    dict_2_update = add_node_interface(ndict[node],ifdata,defaults)
    value.ifindex = dict_2_update.ifindex
    interfaces.append(dict_2_update)

  if not 'name' in link:
    link.name = link_nodes[0].name + " - " + link_nodes[1].name

  for i in range(0,2):
    link[end_names[i]] = { 'node': link_nodes[i]['name'],'ifname': interfaces[i].get('ifname') }

    remote = link_nodes[1-i].name
    interfaces[i]['neighbors'] = [{
        'node': remote,
        'ifname': interfaces[1-i]['ifname']
      }]
    for af in ('ipv4','ipv6'):
      if af in interfaces[1-i]:
        interfaces[i]['neighbors'][0][af] = interfaces[1-i][af]
      if af in interfaces[i]:
        link[end_names[i]][af] = interfaces[i][af]

  return link

def check_link_attributes(data: Box, nodes: dict, valid: set) -> bool:
  ok = True
  for k in data.keys():
    if k not in nodes and k not in valid:
      common.error("Invalid link attributes '%s' in %s" % (k,data),common.IncorrectValue,'links')
      ok = False

  return ok

def set_link_type_role(link: Box, pools: Box, nodes: Box) -> None:
  node_cnt = len(link[IFATTR])      # Set the number of attached nodes (used in many places further on)
  link['node_count'] = node_cnt

  host_count = 0                    # Count the number of hosts attached to the link
  for ifdata in link[IFATTR]:
    if nodes[ifdata.node].get('role','') == 'host':
      host_count = host_count + 1

  if host_count > 0:                # If we have hosts and a single router attached to a non-VLAN link, set link role to 'stub'
    link.host_count = host_count    # ... VLAN case will be set in the VLAN module
    if not 'role' in link and host_count == node_cnt - 1 and not 'vlan_name' in link:
      link.role = 'stub'

  if 'type' in link:                # Link type already set, nothing to do
    return

  link.type = 'lan' if node_cnt > 2 else 'p2p' if node_cnt == 2 else 'stub'     # Set link type based on number of attached nodes

  if host_count > 0:
    link.type = 'lan'

  return

def check_link_type(data: Box) -> bool:
  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  link_type = data.get('type')

  if 'mtu' in data and not isinstance(data.mtu,int): # pragma: no cover
    common.error(f'MTU parameter should be an integer: {data}',common.IncorrectValue,'links')

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

  if not link_type in [ 'stub','p2p','lan','vlan_member']:
    common.error('Invalid link type %s: %s' % (link_type,data),common.IncorrectValue,'links')
    return False
  return True

#
# Interface Feature Check -- validate that the selected addressing works on target lab devices
#

def interface_feature_check(nodes: Box, defaults: Box) -> None:
  for node,ndata in nodes.items():
    features = devices.get_device_features(ndata,defaults)
    for ifdata in ndata.get('interfaces',[]):
      if 'ipv4' in ifdata:
        if isinstance(ifdata.ipv4,bool) and ifdata.ipv4 and \
            not features.initial.ipv4.unnumbered:
          common.error(
            f'Device {ndata.device} does not support unnumbered IPv4 interfaces used on\n'+
            f'.. node {node} interface {ifdata.ifname} (link {ifdata.name})',
            common.IncorrectValue,
            'interfaces')
      if 'ipv6' in ifdata:
        if isinstance(ifdata.ipv6,bool) and ifdata.ipv6 and \
            not features.initial.ipv6.lla:
          common.error(
            f'Device {ndata.device} does not support LLA-only IPv6 interfaces used on\n'+
            f'.. node {node} interface {ifdata.ifname} (link {ifdata.name})',
            common.IncorrectValue,
            'interfaces')

def set_default_gateway(link: Box, nodes: Box) -> None:
  if not 'host_count' in link:      # No hosts attached to the link, get out
    return

  link.pop('host_count',None)
  if not 'gateway' in link:
    gateway = None
    for ifdata in link[IFATTR]:
      if nodes[ifdata.node].get('role','') != 'host' and 'ipv4' in ifdata:
        link.gateway.ipv4 = ifdata.ipv4
        break
  else:
    if not isinstance(ifdata.gateway,dict) or not 'ipv4' in ifdata.gateway:  # pragma: no cover
      common.error(
        f'Gateway attribute specified on {link} is not a dictionary with ipv4 key',
        common.IncorrectValue,
        'links')

  if not 'gateway' in link:         # Didn't find a usable gateway, exit
    return

  for ifdata in link[IFATTR]:                             # Copy link gateway to all hosts attached to the link
    if nodes[ifdata.node].get('role','') == 'host':       # Set gateway only for hosts
      for interface in nodes[ifdata.node].interfaces:     # Find the corresponding host interface
        if link.linkindex == interface.linkindex:
          if interface.ifindex == 1:                      # Set the default gateway only on the first host interface
            interface.gateway = link.gateway

"""
Set node.af flags to indicate that the node has IPv4 and/or IPv6 address family configured
"""
def set_node_af(nodes: Box) -> None:
  for n in nodes.values():
    for af in ['ipv4','ipv6']:
      if af in n.get('loopback',{}):
        n.af[af] = True
        continue

      for l in n.get('interfaces',[]):
        if af in l:
          n.af[af] = True
          continue

def set_linkindex(topology: Box) -> None:
  if not 'links' in topology:
    return

  linkindex = topology.defaults.get('link_index',1)
  for link in topology.links:
    link.linkindex = linkindex
    linkindex = linkindex + 1

def transform(link_list: typing.Optional[Box], defaults: Box, nodes: Box, pools: Box) -> typing.Optional[Box]:
  if not link_list:
    return None

  link_attr_full = get_link_full_attributes(defaults)

  for link in link_list:
    if not check_link_attributes(data=link,nodes=nodes,valid=link_attr_full):
      continue

    set_link_type_role(link=link,pools=pools,nodes=nodes)
    if not check_link_type(data=link):
      continue

    if link.type == 'p2p':
      augment_p2p_link(link,pools,nodes,defaults=defaults)
    else:
      if not 'bridge' in link:
        link['bridge'] = "%s_%d" % (defaults.name[0:10],link.linkindex) # max 15 chars on Linux
      elif len(link['bridge']) > 15:
        common.error(
            f'Bridge name {link["bridge"]} has more than 15 characters',
            common.IncorrectValue,
            'interfaces')
      augment_lan_link(link,pools,nodes,defaults=defaults)

    set_default_gateway(link,nodes)

  interface_feature_check(nodes,defaults)
  set_node_af(nodes)
  return link_list
