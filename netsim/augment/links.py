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
from .. import utils
from ..data.validate import must_be_string,must_be_list,must_be_dict,validate_attributes
from .. import addressing
from . import devices

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

"""
Normalize the list of links:

* Dictionary with 'interfaces' key ==> no change
* Dictionary without 'interfaces' ==> extract nodes into 'interfaces', keep other keys
* List ==> create a dictionary with 'interfaces' element
* String ==> split into list, create a dictionary with 'interfaces' element

"""

def adjust_link_list(links: list, nodes: Box) -> list:
  link_list: list = []

  if not(links):
    return link_list

  link_cnt = 0
  for l in links:
    if isinstance(l,dict) and 'interfaces' in l:                # a dictionary with 'interfaces' element
      l = Box(l,default_box=True,box_dots=True)
      must_be_list(l,'interfaces',f'link[{link_cnt}]',module='links')
      l.interfaces = adjust_interface_list(l.interfaces,l,nodes)
      link_list.append(l)
      continue

    if isinstance(l,Box):                                       # a dictionary without 'interfaces' element
      link_data = Box({},default_box=True,box_dots=True)        # ... split it into link attributes
      link_intf = []                                            # ... and a list of nodes
      for k in l.keys():
        if k in nodes:                                          # Node name -> interface list
          must_be_dict(l,k,f'link[{link_cnt}]',create_empty=True)
          if isinstance(l[k],dict):
            l[k].node = k
            link_intf.append(l[k])
        else:
          link_data[k] = l[k]                                   # ... otherwise copy key/value pair to link data
      link_data.interfaces = link_intf                          # Add revised interface data to link data
      link_list.append(link_data)                               # ... and move on
    elif isinstance(l,list):
      link_list.append(Box({ 'interfaces': adjust_interface_list(l,l,nodes) },default_box=True,box_dots=True))
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
      link_list.append({ 'interfaces': link_intf })
    link_cnt = link_cnt + 1

  if common.debug_active('links'):
    print("Adjusted link list")
    print("=" * 60)
    print(common.get_yaml_string(link_list))

  return link_list

"""
Validate link attributes
"""
def validate(topology: Box) -> None:
  providers = list(topology.defaults.providers.keys())
  for l_data in topology.links:
    linkpath = f'links[{l_data.linkindex}]'           # Topology path to current link
    validate_attributes(
      data=l_data,                                    # Validate link data
      topology=topology,
      data_path=linkpath,
      data_name=f'link',
      attr_list=['link'],                             # We're checking node attributes
      modules=topology.get('module',[]),              # ... against topology modules
      extra_attributes=providers,                     # Allow provider-specific attributes in links
      module_source='topology',
      module='links')                                 # Function is called from 'links' module

    for intf in l_data.interfaces:
      n_data = topology.nodes[intf.node]
      validate_attributes(
        data=intf,                                      # Validate interface data
        topology=topology,
        data_path=f'{linkpath}.{intf.node}',
        data_name=f'interface',
        attr_list=['interface','link'],                 # We're checking interface or link attributes
        modules=n_data.get('module',[]),                # ... against node modules
        module_source=f'nodes.{intf.node}',
        module='links')                                 # Function is called from 'links' module

    # Validate link prefix attributes, but only if it's a dictionary. Other cases will be handled by prefix parsing routines
    if 'prefix' in l_data and isinstance(l_data.prefix,Box):
      validate_attributes(
        data=l_data.prefix,                             # Validate link prefix
        topology=topology,
        data_path=f'{linkpath}.prefix',                 # Topology path to link prefix
        data_name=f'prefix',
        attr_list=['prefix'],                           # We're checking prefix attributes
        modules=None,                                   # No module attributes in prefix
        module='links')

"""
Get the link attributes that have to be propagated to interfaces: full set
of attributes minus the 'no_propagate' attributes 
"""
def get_link_propagate_attributes(defaults: Box) -> set:
  return set(defaults.attributes.link).union(set(defaults.attributes.link_internal)) - \
         set(defaults.attributes.link_no_propagate)

"""
Add interface data structure to a node:

* Add node-specific interface index
* Create interface name
* Add provider-specific interface data
* Cleanup 'af: False' entries
* Handle interface/node/system MTU
"""
def create_regular_interface(node: Box, ifdata: Box, defaults: Box) -> None:
  ifindex_offset = devices.get_device_attribute(node,'ifindex_offset',defaults)
  if ifindex_offset is None:
    ifindex_offset = 1

  # Allow user to select a specific interface index per link
  ifindex = ifdata.get('ifindex',None)

  # When computing default ifindex, consider only non-loopback interfaces
  if not ifindex:
   ifindex = len([intf for intf in node.interfaces if intf.get('type',None) != 'loopback']) + ifindex_offset

  ifname_format = devices.get_device_attribute(node,'interface_name',defaults)

  ifdata.ifindex = ifindex
  if ifname_format and not 'ifname' in ifdata:
    ifdata.ifname = utils.strings.eval_format(ifname_format,ifdata)

  pdata = devices.get_provider_data(node,defaults).get('interface',{})
  pdata = Box(pdata,box_dots=True,default_box=True)                     # Create a copy of the provider interface data
  if 'name' in pdata:
    pdata.name = utils.strings.eval_format(pdata.name,ifdata)

  if pdata:
    provider = devices.get_provider(node,defaults)
    ifdata[provider] = pdata

def create_loopback_interface(node: Box, ifdata: Box, defaults: Box) -> None:
  ifindex_offset = devices.get_device_attribute(node,'loopback_offset',defaults) or 0
  ifdata.ifindex = ifindex_offset + ifdata.linkindex
  ifdata.virtual_interface = True
  ifname_format  = devices.get_device_attribute(node,'loopback_interface_name',defaults)

  if not ifname_format:
    common.error(
      f'Device {node.device}/node {node.name} does not support loopback links',
      common.IncorrectValue,
      'links')
    return

  if not 'ifname' in ifdata:
    ifdata.ifname = utils.strings.eval_format(ifname_format,ifdata)

  # If the device uses 'loopback_offset' then we're assuming it's large enough to prevent overlap with physical interfaces
  # Otherwise, create fake ifindex for loopback interfaces to prevent that overlap
  #
  if not ifindex_offset:
    ifdata.ifindex = 10000 + ifdata.ifindex

def add_node_interface(node: Box, ifdata: Box, defaults: Box) -> Box:
  if ifdata.get('type') == 'loopback':
    create_loopback_interface(node,ifdata,defaults)
  else:
    create_regular_interface(node,ifdata,defaults)

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

"""
Add link attributes (specified in link_attr set) to interface data structure

Also used to merge interface data structure with neighbor data structure when building neighbor list
"""
def interface_data(link: Box, link_attr: set, ifdata: Box) -> Box:
  for k in link_attr:
    if k in link:
      if not k in ifdata:
        ifdata[k] = link[k]
      elif isinstance(link[k],dict) and isinstance(ifdata[k],dict):
        ifdata[k] = link[k] + ifdata[k]
  return ifdata

"""
Set FHRP (anycast/VRRP/...) gateway on a link
"""

def set_fhrp_gateway(link: Box, pfx_list: Box, nodes: Box, link_path: str) -> None:
  gwid = data.get_from_box(link,'gateway.id')
  if not gwid:                                                        # No usable gateway ID, nothing to do
    return

  fhrp_assigned = False
  for af in common.AF_LIST:
    if not af in pfx_list or isinstance(pfx_list[af],bool):           # No usable IPv4/IPv6 prefix, nothing to do
      continue

    try:                                                              # Now try to get N-th IP address on that link
      link.gateway[af] = get_nth_ip_from_prefix(netaddr.IPNetwork(link.prefix[af]),link.gateway.id)
      fhrp_assigned = True
    except Exception as ex:
      common.error(
        f'Cannot generate gateway IP address on {link_path}' + \
        f' from [af] prefix {link.prefix[af]} and gateway ID {link.gateway.id}\n' + \
        common.extra_data_printout(str(ex)),
        common.IncorrectValue,
        'links')
      return

  if not fhrp_assigned:
    return

  for intf in link.interfaces:                                        # Copy link gateway into interface attributes
    if 'gateway' in nodes[intf.node].get('module',[]):                # ... but only for nodes using the gateway module
      for af in common.AF_LIST:
        if af in link.gateway:
          intf.gateway[af] = link.gateway[af]

  if common.debug_active('links'):     # pragma: no cover (debugging)
    print(f'FHRP gateway set for {link}')

"""
Assign a prefix (IPv4+IPv6) to a link:

* If the prefix is already defined, validate it
* If the link is unnumbered, return 'unnumbered' prefix
* Otherwise allocate prefix from a pool

Allocating pool prefix:

* Use addressing pool specified in link.pool
* Otherwise, if link.role is set, add that to a list of pool candidates
* Allocate a prefix from the first available candidate pool
"""

def assign_link_prefix(
      link: Box,
      pools: typing.List[str],
      addr_pools: Box,
      nodes: Box,
      link_path: str = 'links') -> Box:
  if 'prefix' in link:                                    # User specified a static link prefix
    pfx_list = addressing.parse_prefix(link.prefix)
    if isinstance(link.prefix,str):
      link.prefix = addressing.rebuild_prefix(pfx_list)   # convert str to prefix dictionary

    set_fhrp_gateway(link,pfx_list,nodes,link_path)
    return pfx_list

  if 'unnumbered' in link:                                # User requested an unnumbered link
    link.prefix = Box({ 'unnumbered': True })
    return link.prefix

  if must_be_string(link,'pool',link_path):
    if not link.pool in addr_pools:
      common.error(
        f'Unknown address pool {link.pool} used in {link_path}',
        common.IncorrectValue,
        'links')
    pools = [ link.pool ] + pools
  else:
    if must_be_string(link,'role',link_path):
      pools = [ link.get('role') ] + pools

  pfx_list = addressing.get(addr_pools,pools)
  link.prefix = {
      af: str(v) if af in common.AF_LIST and not isinstance(v,bool) else v for af,v in pfx_list.items()
    }
  if not link.prefix:
    link.pop('prefix',None)

  set_fhrp_gateway(link,pfx_list,nodes,link_path)
  return pfx_list

"""
Get IPAM policy for link/prefix

* If the prefix is a bool ==> unnumbered
* If the link is a P2P link ==> p2p (for backward compatibility)
* If the prefix is large enough ==> id_based
* Otherwise use sequential policy

Return 'error' if the prefix size is too small
"""
def get_prefix_IPAM_policy(link: Box, pfx: typing.Union[netaddr.IPNetwork,bool], ndict: Box) -> str:
  if isinstance(pfx,bool):
    return 'unnumbered'

  gwid = data.get_from_box(link,'gateway.id') or 0                    # Get link gateway ID (if set) --- must be int for min to work
  if link.type == 'p2p' and not gwid:                                 # P2P allocation policy cannot be used with default gateway
    return 'p2p' if pfx.first != pfx.last else 'error'

  pfx_size = pfx.last - pfx.first + 1
  add_extra_ip = 0
  subtract_reserved_ip = -2

  if pfx_size > 2:
    if gwid > 0:                                                      # Gateway ID at the front of the subnet -- need one extra IP
      add_extra_ip = 1
    if gwid < 0:                                                      # Don't allow node address allocation beyond last-in-subnet gateway
      subtract_reserved_ip = min(subtract_reserved_ip,gwid)

    pfx_size = pfx_size + subtract_reserved_ip

  max_id = max([ ndict[intf.node].id for intf in link.interfaces if intf.node in ndict ])
  if max_id < pfx_size:                                               # If we can fit all node IDs attached to this link into the prefix
    return 'id_based'                                                 # ... we'll use ID-based address allocation
  if len(link.interfaces) + add_extra_ip < pfx_size:                  # Otherwise, if the prefix is big enough
    return 'sequential'                                               # ... we'll use sequential address allocation

  if pfx_size < 2 and link.type == 'loopback':                        # Final straw: maybe we're dealing with a loopback?
    return 'loopback'

  return 'error'

"""
Get Nth IP address in a prefix returned as a nice string with a subnet mask

*** WARNING *** WARNING *** WARNING ***

Parent must catch the exception as we don't know what error text to display
"""

def get_nth_ip_from_prefix(pfx: netaddr.IPNetwork, n_id: int) -> str:
  node_addr = netaddr.IPNetwork(pfx[n_id])
  node_addr.prefixlen = pfx.prefixlen
  return str(node_addr)

"""
Set an interface address based on the link prefix and interface sequential number (could be node.id or counter)
"""
def set_interface_address(intf: Box, af: str, pfx: netaddr.IPNetwork, node_id: int) -> bool:
  if af in intf:                                # Check static interface addresses
    if isinstance(intf[af],bool):               # unnumbered or unaddressed node, leave it alone
      return True

    if isinstance(intf[af],int):                # host portion of IP address specified as an integer
      node_id = intf[af]
    elif isinstance(intf[af],str):              # static address specified on the interface
      try:
        intf_pfx = netaddr.IPNetwork(intf[af])  # Try to parse the interface IP address
        if not '/' in intf[af]:
          intf_pfx.prefixlen = pfx.prefixlen    # If it lacks a prefix, add link prefix
        intf[af] = str(intf_pfx)                # ... and save modified/validated interface IP address
      except Exception as ex:
        common.error(
          f'Cannot parse {af} address {intf.af} for node {intf.node}\n'+common.extra_data_printout(str(ex)),
          common.IncorrectValue,
          'links')
        return False

      if str(intf_pfx) != str(intf_pfx.cidr):   # Does the IP address have host bits -- is it different from its CIDR subnet?
        return True                             # That's it -- the user knows what she's doing

      if intf_pfx.last <= intf_pfx.first + 1:   # Are we dealing with special prefix (loopback or /31)
        return True                             # ... then it's OK not to have host bits

      common.error(
        f'Address {intf.af} for node {intf.node} does not contain host bits',
        common.IncorrectValue,
        'links')
      return False

  # No static interface address, or static address specified as relative node_id
  try:
    intf[af] = get_nth_ip_from_prefix(pfx,node_id)
    return True
  except Exception as ex:
    common.error(
      f'Cannot assign host index {node_id} in {af} from prefix {str(pfx)} to node {intf.node}\n' + \
          common.extra_data_printout(str(ex)),
      common.IncorrectValue,
      'links')

  return False

"""
Unnumbered AF IPAM -- set interface address to 'True'

If the interface address is set, validate that it's a valid address (can't be int)
"""
def IPAM_unnumbered(link: Box, af: str, pfx: typing.Optional[bool], ndict: Box) -> None:
  for intf in link.interfaces:
    if not af in intf:            # No static address, set it to link bool value or use loopback AF presence for old-style unnumbereds
      intf[af] = pfx if isinstance(pfx,bool) else bool(data.get_from_box(ndict[intf.node],f'loopback.{af}'))
    elif data.is_true_int(intf[af]):
      common.error(
        f'Node {intf.node} is using host index {intf[af]} for {af} on an unnumbered link',
        common.IncorrectValue,
        'links')

def IPAM_sequential(link: Box, af: str, pfx: netaddr.IPNetwork, ndict: Box) -> None:
  start = 1 if pfx.last != pfx.first + 1 else 0
  gwid = data.get_from_box(link,'gateway.id')
  for count,intf in enumerate(link.interfaces):
    if count + start == gwid:                                   # Would the next address overlap with gateway ID
      start = start + 1                                         # ... no big deal, just move the starting point ;)
    set_interface_address(intf,af,pfx,count+start)

def IPAM_p2p(link: Box, af: str, pfx: netaddr.IPNetwork, ndict: Box) -> None:
  start = 1 if pfx.last != pfx.first + 1 else 0
  for count,intf in enumerate(sorted(link.interfaces, key=lambda intf: intf.node)):
    set_interface_address(intf,af,pfx,count+start)

def IPAM_id_based(link: Box, af: str, pfx: netaddr.IPNetwork, ndict: Box) -> None:
  for intf in link.interfaces:
    set_interface_address(intf,af,pfx,ndict[intf.node].id)

def IPAM_loopback(link: Box, af: str, pfx: netaddr.IPNetwork, ndict: Box) -> None:
  for intf in link.interfaces:
    pfx.prefixlen = 128 if ':' in str(pfx) else 32
    intf[af] = str(pfx)

IPAM_dispatch: typing.Final[dict] = { 
    'unnumbered': IPAM_unnumbered,
    'p2p': IPAM_p2p,
    'sequential': IPAM_sequential,
    'id_based': IPAM_id_based,
    'loopback': IPAM_loopback
  }

"""
Assign addresses to all interfaces on a link

* Skip if the link has no usable prefix (l2only link)
* Use IPAM_unnumbered on old-style unnumbered links
* Figure out allocation policies (based on link type, prefix size, number of interfaces)
* Execute selected IPAM routing
"""
def assign_interface_addresses(link: Box, addr_pools: Box, ndict: Box, defaults: Box) -> None:
  global IPAM_dispatch
  pfx_list = link.get('prefix',None)
  if not pfx_list:
    return

  if 'unnumbered' in pfx_list:                        # Deal with unnumbered links first
    for af in ('ipv4','ipv6'):
      pfx_list.pop(af)                                # Remove AF prefix from unnumbered link
      IPAM_unnumbered(link,af,None,ndict)

    link.pop('prefix')
    return

  for af in ('ipv4','ipv6'):
    if not af in pfx_list:                            # Skip address families not used on the link
      continue

    if isinstance(pfx_list[af],bool):                 # Unnumbered AF
      allocation_policy = 'unnumbered'
      pfx_net = pfx_list[af]
    else:
      try:                                            # Parse the AF prefix
        pfx_net = netaddr.IPNetwork(pfx_list[af])
      except Exception as ex:                         # Report an error and move on if it cannot be parsed
        common.error(
          f'Cannot parse {af} prefix {pfx_list[af]} on link#{link.linkindex}\n' + \
            common.extra_data_printout(f'{ex}') + '\n' + \
            common.extra_data_printout(f'{link}'),
          common.IncorrectValue,
          'links')
        continue

      if 'allocation' in pfx_list:
        allocation_policy = pfx_list.allocation
      else:
        allocation_policy = get_prefix_IPAM_policy(link,pfx_net,ndict)    # get IPAM policy based on prefix and link size

    if allocation_policy == 'error':                                      # Something went wrong, cannot assing IP addresses
      rq = f'{len(link.interfaces)} nodes'
      if data.get_from_box(link,'gateway.id'):
        rq = rq + f' plus first-hop gateway'
      common.error(
        f'Cannot use {af} prefix {pfx_list[af]} to address {rq} on link#{link.linkindex}\n' + \
        common.extra_data_printout(f'link data: {link}',width=90),
        common.IncorrectValue,
        'links')
      continue

    if not allocation_policy in IPAM_dispatch:
      common.error(
        f'Invalid IP address allocation policy specified in prefix {pfx_list} found on links[{link.linkindex}]',
        common.IncorrectValue,
        'links')
    IPAM_dispatch[allocation_policy](link,af,pfx_net,ndict)               # execute IPAM policy to get AF addresses on interfaces

"""
cleanup 'af: False' entries from interfaces
"""
def cleanup_link_interface_AF_entries(link: Box) -> None:
  for af in ('ipv4','ipv6'):                    # Iterate over address families
    for intf in link.interfaces:                # ... and link interfaces
      if not af in intf:                        # Nothing to check
        continue

      if intf[af] is False:                     # Address set to false makes no sense ==> remove
        intf.pop(af,None)
        continue

      if isinstance(intf[af],bool):             # Address set to true. Unnumbered, move on
        continue

      if data.is_true_int(intf[af]):            # Unprocessed int. Must be node index on an unnumbered link ==> error
        common.error(
          f'Interface ID for node {intf.node} did not result in a usable address on link#{link.linkindex}\n' + \
            common.extra_data_printout(f'{link}'),
          common.IncorrectType,
          'links')
        continue

      if not '/' in intf[af]:                   # Subnet mask is unknown
        common.error(
          f'Unknown subnet mask for {af} address {intf[af]} used by node {intf.node} on link#{link.linkindex}\n' + \
            common.extra_data_printout(f'{link}'),
          common.IncorrectType,
          'links')
        continue

"""
Calculate interface description:

* Link name (if exists)
* Stub link (on a link with a single node)
* A -> B when a link has two nodes
* A -> [ B,C,D ] when a link has more than two nodes
"""
def set_interface_name(ifdata: Box, link: Box, ifcnt: int) -> None:
  if 'name' in link:
    ifdata.name = link.name
    return

  node_name = link.interfaces[ifcnt].node
  if len(link.interfaces) == 1:
    ifdata.name = f'{node_name} -> stub'
    return

  n_list = [ link.interfaces[i].node for i in range(0,len(link.interfaces)) if i != ifcnt ]
  if len(n_list) == 1:
    ifdata.name = f'{node_name} -> {n_list[0]}'
  else:
    ifdata.name = f'{node_name} -> [{",".join(list(n_list))}]'

"""
Create node interfaces from link interfaces
"""
def create_node_interfaces(link: Box, addr_pools: Box, ndict: Box, defaults: Box) -> None:
  link_attr_propagate = get_link_propagate_attributes(defaults)

  if common.debug_active('links'):     # pragma: no cover (debugging)
    print(f'\nCreate node interfaces: {link} using {link_attr_propagate}')

  interfaces = []
  for (intf_cnt,value) in enumerate(link.interfaces):
    node = value.node
    #
    # Create node interface data from interfaces attributes augmented with link attributes
    # and node-relevant link module attributes
    ifdata = interface_data(
                link=link,
                link_attr=link_attr_propagate.union(ndict[node].get('module',[])) - set(defaults.attributes.link_module_no_propagate),
                ifdata=Box(value))
    set_interface_name(ifdata,link,intf_cnt)
    ifdata.pop('node',None)                                       # Remove the node name (not needed within the node)
    node_intf = add_node_interface(ndict[node],ifdata,defaults)   # Attach new interface to its node
    value.ifindex = node_intf.ifindex                             # Save ifindex and ifname in link interface data
    value.ifname  = node_intf.ifname                              # ... needed for things like Graph output module that works with links
    interfaces.append({ 'node': node, 'data': node_intf })        # Save newly-created interface for the next step
                                                                  # ... must use dict not Box as Box creates a copy of the data structure

  if common.debug_active('links'):     # pragma: no cover (debugging)
    print(f'... link data: {link}')
    print(f'... interface data: {interfaces}\n')

  # Second phase: build neighbor list from list of newly-created interfaces
  for node_if in interfaces:
    ifdata = node_if['data']                                      # Get a pointer to interface data
    ifdata.neighbors = []
    for remote_if in interfaces:                                  # Iterate over all interfaces created from this link
      if remote_if is node_if:                                    # ... and skip the current interface
        continue
      remote_node = remote_if['node']                             # Remote node name in a handier format
      remote_ifdata = remote_if['data']                           # ... and a pointer to remote interface data
      ngh_data = Box({ 'ifname': remote_ifdata.ifname, 'node': remote_node })
      #
      # Find relevant modules that have interface attributes
      mods_with_attr = set([ m for m in ndict[remote_node].get('module',[])
                              if defaults[m].attributes.get('interface',None) or
                                 defaults[m].attributes.get('link_to_neighbor',None) ])
      #
      # Merge neighbor module data + AF with baseline neighbor data
      ngh_data = interface_data(
                   link=remote_ifdata,
                   link_attr=mods_with_attr.union(['ipv4','ipv6']),
                   ifdata=ngh_data)
      ifdata.neighbors.append(ngh_data)

def set_link_loopback_type(link: Box, nodes: Box, defaults: Box) -> None:
  node = link.interfaces[0].node
  ndata = nodes[node]
  features = devices.get_device_features(ndata,defaults)

  lb_name = devices.get_device_attribute(ndata,'loopback_interface_name',defaults)
  if not lb_name:
    return

  if features.stub_loopback is False:
    return

  if not defaults.links.stub_loopback and not features.stub_loopback:
    return

  link.type = 'loopback'

def set_link_type_role(link: Box, pools: Box, nodes: Box, defaults: Box) -> None:
  node_cnt = len(link.interfaces)   # Set the number of attached nodes (used in many places further on)
  link['node_count'] = node_cnt

  host_count = 0                    # Count the number of hosts attached to the link
  for ifdata in link.interfaces:
    if nodes[ifdata.node].get('role','') == 'host':
      host_count = host_count + 1

  if host_count > 0:                # If we have hosts and a single router attached to a non-VLAN link, set link role to 'stub'
    link.host_count = host_count    # ... VLAN case will be set in the VLAN module
    if not 'role' in link and host_count == node_cnt - 1 and not 'vlan_name' in link:
      link.role = 'stub'

  if 'type' in link:                # Link type already set, nothing to do
    return

  link.type = 'lan' if node_cnt > 2 else 'p2p' if node_cnt == 2 else 'stub'     # Set link type based on number of attached nodes
  if node_cnt == 1:
    set_link_loopback_type(link,nodes,defaults)

  if host_count > 0:
    link.type = 'lan'

  return

def set_link_bridge_name(link: Box, defaults: Box) -> None:
  if link.type in ['p2p','loopback','vlan_member']:                   # No need for bridge names on P2P links, loopbacks and virtual links
    return
  if not 'bridge' in link:
    link['bridge'] = "%s_%d" % (defaults.name[0:10],link.linkindex)   # max 15 chars on Linux
  elif len(link['bridge']) > 15:
    common.error(
      f'Bridge name {link["bridge"]} has more than 15 characters',
      common.IncorrectValue,
      'interfaces')

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

  if link_type == 'loopback' and node_cnt != 1:
    common.error(
      f'Looopback link can have a single node attached: links[{data.linkindex}]\n... {data}',
      common.IncorrectValue,
      'links')
    return False

  if not link_type in [ 'stub','p2p','lan','loopback','vlan_member']:
    common.error(
      f'Invalid link type {link_type} in links[{data.linkindex}]\n... {data}',
      common.IncorrectValue,
      'links')
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

  # No IPv4 prefix on the link or unnumbered IPv4 link
  if not 'ipv4' in link.prefix or isinstance(link.prefix.ipv4,bool):
    return

#  if 'vlan_name' in link:                                 # Do not try to set first-hop gateways on VLAN links, VLAN module will do that
#    return

  if common.debug_active('links'):
    print(f'Set DGW for {link}')
  if not 'gateway' in link:
    gateway = None
    for ifdata in link.interfaces:
      if nodes[ifdata.node].get('role','') != 'host' and ifdata.get('ipv4',False):
        link.gateway.ipv4 = ifdata.ipv4
        break
  elif link.gateway is False:
    return

  if not 'gateway' in link or not isinstance(link.gateway,Box) or not 'ipv4' in link.gateway: # Didn't find a usable gateway, exit
    if common.debug_active('links'):
      print('... not found')
    return

  if common.debug_active('links'):
    print(f'... DGW: {link.gateway}')

  for ifdata in link.interfaces:                          # Copy link gateway to all hosts attached to the link
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

  for link in link_list:
    set_link_type_role(link=link,pools=pools,nodes=nodes,defaults=defaults)
    if not check_link_type(data=link):
      continue

    set_link_bridge_name(link,defaults)
    link_default_pools = ['p2p','lan'] if link.type == 'p2p' else ['lan']
    assign_link_prefix(link,link_default_pools,pools,nodes,f'links[{link.linkindex}]')
    assign_interface_addresses(link,pools,nodes,defaults)
    create_node_interfaces(link,pools,nodes,defaults=defaults)

    cleanup_link_interface_AF_entries(link)
    set_default_gateway(link,nodes)

  interface_feature_check(nodes,defaults)
  set_node_af(nodes)
  return link_list
