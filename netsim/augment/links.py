#
# Create detailed link data structures including automatic interface numbering
# from high-level topology
#
import typing

import netaddr
from box import Box

# Related modules
from ..utils import log,strings
from .. import data
from ..data.validate import validate_attributes,get_object_attributes
from ..data.types import must_be_string,must_be_list,must_be_dict,must_be_id
from . import devices,addressing

VIRTUAL_INTERFACE_TYPES: typing.Final[typing.List[str]] = [
  'loopback', 'tunnel', 'lag' ]

def adjust_interface_list(iflist: list, link: Box, nodes: Box) -> list:
  link_intf = []
  intf_cnt  = 0
  for n in iflist:                      # Sanity check of interface data
    intf_cnt = intf_cnt + 1
    if isinstance(n,str):               # Another shortcut: node name as string
      if not n in nodes:                # ... is it a valid node name?
        log.error(                   # ... it's not, get lost
          f'Interface {link._linkname}.interfaces.{intf_cnt} refers to an unknown node {n}',
          log.IncorrectValue,
          'links')
        continue
      n = data.get_box({ 'node': n })
      
    if not isinstance(n,Box):          # Still facing non-dict data type?
      log.error(                     # ... report an error
        f'Interface data in {link._linkname}.interfaces[{intf_cnt}] must be a dictionary, found {type(n).__name__}',
        log.IncorrectValue,
        'links')
    elif not 'node' in n:               # Do we have node name in interface data?
      log.error(                     # ... no? Too bad, throw an error
        text=f'Interface data {link._linkname}.interfaces[{intf_cnt}] is missing a "node" attribute',
        more_data=[ f'found {n}' ],
        category=log.MissingValue,
        module='links')
    elif not n.node in nodes:           # Is the node name valid?
      log.error(                     # ... it's not, get lost
        f'Interface data {link._linkname}.interfaces[{intf_cnt}] refers to an unknown node {n.node}',
        log.IncorrectValue,
        'links')
    else:
      link_intf.append(n)               # Interface data is OK, append it to interface list

  return link_intf

"""
Normalize the link objects:

* Dictionary with 'interfaces' key ==> no change
* Dictionary without 'interfaces' ==> extract nodes into 'interfaces', keep other keys
* List ==> create a dictionary with 'interfaces' element
* String ==> split into list, create a dictionary with 'interfaces' element

"""

def adjust_link_object(l: typing.Any, linkname: str, nodes: Box) -> typing.Optional[Box]:
  if isinstance(l,dict) and not isinstance(l,Box):            # transform dict into Box if needed
    l = data.get_box(l)

  if isinstance(l,Box) and 'interfaces' in l:                 # a dictionary with 'interfaces' element
    l._linkname = linkname
    must_be_list(l,'interfaces',linkname,module='links')
    l.interfaces = adjust_interface_list(l.interfaces,l,nodes)
    return l

  if isinstance(l,Box):                                       # a dictionary without 'interfaces' element
    link_data = data.get_empty_box()                          # ... split it into link attributes
    link_intf = []                                            # ... and a list of nodes
    link_data._linkname = linkname                            # ... set link name
    for k in l.keys():
      if k in nodes:                                          # Node name -> interface list
        must_be_dict(l,k,linkname,create_empty=True)
        if isinstance(l[k],dict):
          l[k].node = k
          link_intf.append(l[k])
      else:
        link_data[k] = l[k]                                   # ... otherwise copy key/value pair to link data
    link_data.interfaces = link_intf                          # Add revised interface data to link data
    return link_data

  if isinstance(l,list):                                              # List of nodes, transform into interfaces
    link_data = data.get_box({ '_linkname' : linkname })              # ... create stub link data structure
    link_data.interfaces = adjust_interface_list(l,link_data,nodes)   # ... and adjust interface list
    return link_data

  if isinstance(l,str):                                       # String, split into a list of nodes
    link_intf = []
    for n in l.split('-'):                # ... split it into a list of nodes
      n = n.strip()                       # ... strip leading and trailing spaces (fixing #816)
      valid_node = n in nodes
      if not valid_node:
        valid_node = len([ x for x in nodes if n.startswith(x) ]) > 0

      if valid_node:                      # If the node name is valid
        link_intf.append({ 'node': n })   # ... append it to the list of interfaces
      else:
        log.error(
          f'Link string {l} in {linkname} refers to an unknown node {n}',
          log.IncorrectValue,
          'links')
    return data.get_box({
      'interfaces': link_intf,
      '_linkname' : linkname })

  log.error(
    f'Invalid type {type(l).__name__} for {linkname}',
    log.IncorrectType,
    'links')
  return None

def adjust_link_list(
      links: typing.Any, 
      nodes: Box,
      linkname_format: str = 'links[{link_cnt}]') -> list:
  link_list: list = []

  if not(links):
    return link_list

  link_cnt = 0
  linkname_path = linkname_format.split("[")[0]
  if isinstance(links,Box):
    for lgn,lgdata in links.items():
      ln_comps = linkname_format.split('[')
      ln_group = f'{ln_comps[0]}.{lgn}[{ln_comps[1]}'
      link_list.extend(adjust_link_list(lgdata,nodes,ln_group))
  elif isinstance(links,list):
    for l in links:
      link_cnt = link_cnt + 1
      linkname = linkname_format.format(link_cnt=link_cnt)
      link_data = adjust_link_object(l,linkname,nodes)
      if not link_data is None:
        if link_data.get('disable',False) is True:
          continue
        link_list.append(link_data)
  elif isinstance(links,str):
    link_list.append(adjust_link_object(links,linkname_path,nodes))
  else:
    log.error(
      f'{linkname_path} must be a list or dictionary',
      log.IncorrectType,
      'links')

  if log.debug_active('links'):
    print("Adjusted link list")
    print("=" * 60)
    print(strings.get_yaml_string(link_list))

  return link_list

"""
Validate link attributes
"""
def validate(topology: Box) -> None:
  # Allow provider-specific global attributes
  providers = get_object_attributes(['providers'],topology)

  for l_data in topology.links:
    validate_attributes(
      data=l_data,                                    # Validate link data
      topology=topology,
      data_path=l_data._linkname,
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
        data_path=f'{l_data._linkname}.{intf.node}',
        data_name=f'interface',
        attr_list=['interface','link'],                 # We're checking interface or link attributes
        modules=n_data.get('module',[]),                # ... against node modules
        extra_attributes=providers,                     # Allow provider-specific attributes in interfaces
        module_source=f'nodes.{intf.node}',
        module='links')                                 # Function is called from 'links' module

"""
Get the link attributes that have to be propagated to interfaces: full set
of attributes minus the 'no_propagate' attributes 
"""
def get_link_propagate_attributes(defaults: Box) -> set:
  return set(defaults.attributes.link).union(set(defaults.attributes.link_internal)) - \
         set(defaults.attributes.link_no_propagate)

"""
get_unique_ifindex: given interface type, and a start and stop value, find a unique ifindex
"""
def get_unique_ifindex(
      node: Box,
      iftype: typing.Optional[str] = None,
      start: int = 1, stop: typing.Optional[int] = None) -> int:
  if stop is None:                                # Assume we can have at most 1000 interfaces of a given type
    stop = start + 1000

  idx_list = [                                    # Build a list of already-used ifindex values
    intf.ifindex for intf in node.interfaces 
      if iftype == intf.type or (iftype is None and intf.type not in VIRTUAL_INTERFACE_TYPES) ]
  ifindex = start
  while ifindex < stop:                           # Iterate through ifindex values
    if ifindex not in idx_list:                   # ... returning the first one that is not used
      return ifindex
    ifindex = ifindex + 1

  log.error(                                      # Ouch, ran out of values :(
    'Cannot get a unique interface index between {start} and {stop} for node {node.name}',
    category=log.IncorrectValue,
    module='links')
  return start + len(node.interfaces) + 1         # Return something just to keep going (we'll fail anyway)

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
  if 'ifindex' not in ifdata:
    ifdata.ifindex = get_unique_ifindex(node,start=ifindex_offset)
  else:
    node._set_ifindex = True
    if ifdata.ifindex < ifindex_offset:
      log.error(
        f'Interface ifindex for device {node.device} (node {node.name}) cannot be lower than {ifindex_offset}',
        category=log.IncorrectValue,
        more_data = [ 'Interface data: ', str(ifdata) ],
        module='links')

  # Set interface name -- either in 'ifname' field (for the "real" interface name)
  # or in the "netlab_ifname" field to track what netlab would have generated
  #
  ifname_format = devices.get_device_attribute(node,'interface_name',defaults)
  if ifname_format:
    ifn_field = 'ifname' if 'ifname' not in ifdata else 'netlab_ifname'
    ifdata[ifn_field] = strings.eval_format(ifname_format,ifdata)

  pdata = devices.get_provider_data(node,defaults).get('interface',{})
  pdata = data.get_box(pdata)                     # Create a copy of the provider interface data
  if 'name' in pdata:
    pdata.name = strings.eval_format(pdata.name,ifdata)

  if pdata:
    provider = devices.get_provider(node,defaults)
    ifdata[provider] = pdata

def create_virtual_interface(node: Box, ifdata: Box, defaults: Box) -> None:
  devtype = ifdata.get('type','loopback')         # Get virtual interface type, default to loopback interface
  ifindex_offset = (
    devices.get_device_attribute(node,f'{devtype}_offset',defaults) or
    1 if devtype == 'loopback' else 0)            # Loopback interfaces have to start with 1 to prevent overlap with built-in loopback

  # Adjust ifindex to prevent overlap between device types
  #
  devtype_offset = (VIRTUAL_INTERFACE_TYPES.index(devtype)+1) * 10000

  ifdata.virtual_interface = True
  ifdata.pop('bridge',None)

  if 'ifindex' not in ifdata:
    ifdata.ifindex = get_unique_ifindex(node,iftype=devtype,start=ifindex_offset+devtype_offset)

  if 'ifname' in ifdata:
    return

  # If we can get the interface name format, create interface name using a reduced
  # ifindex. For example, loopback interfaces have ifindex starting with 10001, but
  # the interface names start with Loopback1
  #
  ifname_format  = devices.get_device_attribute(node,f'{devtype}_interface_name',defaults)
  if ifname_format:
    ifdata.ifname = strings.eval_format(ifname_format,ifdata + { 'ifindex': ifdata.ifindex - devtype_offset })
    return

  # We could not find the relevant interface name template. Report an error
  #
  if devtype == 'loopback':
    log.error(
      f'Device {node.device}/node {node.name} does not support loopback links',
      log.IncorrectValue,
      'links')
  else:
    log.error(
      f'Need explicit interface name (ifname) for {devtype} interface on node {node.name} ({node.device})',
      category=log.IncorrectValue,
      more_data=str(ifdata),
      module='links')

def add_node_interface(node: Box, ifdata: Box, defaults: Box) -> Box:
  if ifdata.get('type',None) in VIRTUAL_INTERFACE_TYPES:
    create_virtual_interface(node,ifdata,defaults)
  else:
    create_regular_interface(node,ifdata,defaults)

  for af in ('ipv4','ipv6'):
    if af in ifdata and not ifdata[af]:
      del ifdata[af]

  if node.get('mtu',None):                      # Is node-level MTU defined (node setting, lab default or device default)
    sys_mtu = devices.get_device_features(node,defaults).initial.get('system_mtu',False)
    if 'mtu' in ifdata:                         # Is MTU defined on the interface?
      if sys_mtu and node.mtu == ifdata.mtu:    # .. is it equal to node MTU?
        ifdata.pop('mtu',None)                  # .... remove interface MTU on devices that support system MTU
    else:                                       # Node MTU is defined, interface MTU is not
      if not sys_mtu:                           # .. does the device support system MTU?
        ifdata.mtu = node.mtu                   # .... no, copy node MTU to interface MTU

  if ifdata.get('type',None) == 'loopback':
    ifdata.pop('mtu',None)                      # Remove MTU from loopback interfaces

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
Get gateway ID -- return None if not set or if 'gateway' is not a dict
"""
def get_gateway_id(link: Box) -> typing.Optional[int]:
  if not isinstance(link.get('gateway',None),Box):
    return None
  return link.gateway.get('id',None)

"""
Set FHRP (anycast/VRRP/...) gateway on a link
"""

def set_fhrp_gateway(link: Box, pfx_list: Box, nodes: Box, link_path: str) -> None:
  gwid = get_gateway_id(link)
  if not gwid:                                                        # No usable gateway ID, nothing to do
    return

  fhrp_assigned = False
  for af in log.AF_LIST:
    if not af in pfx_list or isinstance(pfx_list[af],bool):           # No usable IPv4/IPv6 prefix, nothing to do
      continue

    try:                                                              # Now try to get N-th IP address on that link
      link.gateway[af] = get_nth_ip_from_prefix(netaddr.IPNetwork(link.prefix[af]),link.gateway.id)
      fhrp_assigned = True
    except Exception as ex:
      log.error(
        f'Cannot generate gateway IP address on {link_path}' + \
        f' from [af] prefix {link.prefix[af]} and gateway ID {link.gateway.id}\n' + \
        strings.extra_data_printout(str(ex)),
        log.IncorrectValue,
        'links')
      return

  if not fhrp_assigned:
    return

  if log.debug_active('links'):     # pragma: no cover (debugging)
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

  if 'prefix' in link:                                    # Does the link have prefix parameters?
    pfx_data = addressing.parse_prefix(link.prefix,path=link_path)
    if log.debug_active('addr'):                          # pragma: no cover (debugging printout)
      print(f'link {link_path} got prefix {pfx_data} from {link.prefix}')
    
    if link.prefix is False:                              # There should be no prefix on this link, get out
      return pfx_data

    if isinstance(link.prefix,str):                       # Is the prefix an IPv4 address?
      link.prefix = addressing.rebuild_prefix(pfx_data)   # ... convert it to prefix dictionary

    set_fhrp_gateway(link,pfx_data,nodes,link_path)       # Try to set the FHRP gateway
    #
    # Did we get a usable prefix? It should be empty (l2only) or have IPv4 or IPv6 prefix
    if not pfx_data or 'ipv4' in pfx_data or 'ipv6' in pfx_data:
      return pfx_data

  else:                                                   # No prefix parameters on the link
    pfx_data = data.get_empty_box()

  if 'unnumbered' in link:                                # User requested an unnumbered link
    link.prefix = data.get_box({ 'unnumbered': True })
    return link.prefix

  if must_be_string(link,'pool',link_path):
    if not link.pool in addr_pools:
      log.error(
        f'Unknown address pool {link.pool} used in {link_path}',
        log.IncorrectValue,
        'links')
    pools = [ link.pool ] + pools
  else:
    if must_be_string(link,'role',link_path):
      pools = [ link.get('role') ] + pools

  pfx_list = addressing.get(addr_pools,pools)
  link.prefix = {
      af: str(v) if af in log.AF_LIST and not isinstance(v,bool) else v for af,v in pfx_list.items()
    }
  if pfx_data:                                            # Was there some extra prefix data specified on the link?
    link.prefix += pfx_data                               # Add that to the pool prefix
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

  gwid = get_gateway_id(link) or 0                                    # Get link gateway ID (if set) --- must be int for min to work
  if link.type == 'p2p' and not gwid:                                 # P2P allocation policy cannot be used with default gateway
    return 'p2p' if pfx.first != pfx.last else 'error'

  pfx_size = pfx.last - pfx.first + 1
  add_extra_ip = 0
  subtract_reserved_ip = -2

  if pfx_size > 2:
    if gwid > 0:                                                      # Gateway ID at the front of the subnet -- need one extra IP
      add_extra_ip = 1
    if gwid < 0:                                                      # Don't allow node address allocation beyond last-in-subnet gateway
      subtract_reserved_ip = min(subtract_reserved_ip,gwid-1)

    pfx_size = pfx_size + subtract_reserved_ip
  elif pfx_size == 2 and len(link.interfaces) == 2:
    return 'p2p'

  max_id = max([ ndict[intf.node].id for intf in link.interfaces if intf.node in ndict ])
  if pfx_size == 1:                                                   # Do we have a single node attached to a /32 link?
    return 'loopback' if len(link.interfaces) == 1 else 'error'       # ... if so, we'll use loopback address allocation

  if max_id <= pfx_size:                                              # If we can fit all node IDs attached to this link into the prefix
    return 'id_based'                                                 # ... we'll use ID-based address allocation
  if len(link.interfaces) + add_extra_ip <= pfx_size:                 # Otherwise, if the prefix is big enough
    return 'sequential'                                               # ... we'll use sequential address allocation

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
        log.error(
          f'Cannot parse {af} address {intf.af} for node {intf.node}\n'+strings.extra_data_printout(str(ex)),
          log.IncorrectValue,
          'links')
        return False

      if str(intf_pfx) != str(intf_pfx.cidr):   # Does the IP address have host bits -- is it different from its CIDR subnet?
        return True                             # That's it -- the user knows what she's doing

      if intf_pfx.last <= intf_pfx.first + 1:   # Are we dealing with special prefix (loopback or /31)
        return True                             # ... then it's OK not to have host bits

      log.error(
        f'Address {intf[af]} for node {intf.node} does not contain host bits',
        log.IncorrectValue,
        'links')
      return False

  # No static interface address, or static address specified as relative node_id
  try:
    intf[af] = get_nth_ip_from_prefix(pfx,node_id)
    return True
  except Exception as ex:
    log.error(
      f'Cannot assign host index {node_id} in {af} from prefix {str(pfx)} to node {intf.node}\n' + \
          strings.extra_data_printout(str(ex)),
      log.IncorrectValue,
      'links')

  return False

"""
Unnumbered AF IPAM -- set interface address to 'True'

If the interface address is set, validate that it's a valid address (can't be int)
"""
def IPAM_unnumbered(link: Box, af: str, pfx: typing.Optional[bool], ndict: Box) -> None:
  for intf in link.interfaces:
    if not af in intf:            # No static address, set it to link bool value or use loopback AF presence for old-style unnumbereds
      intf[af] = pfx if isinstance(pfx,bool) else bool(ndict[intf.node].get(f'loopback.{af}',False))
    elif data.is_true_int(intf[af]):
      log.error(
        f'Node {intf.node} is using host index {intf[af]} for {af} on an unnumbered link',
        log.IncorrectValue,
        'links')

def IPAM_sequential(link: Box, af: str, pfx: netaddr.IPNetwork, ndict: Box) -> None:
  start = 1 if pfx.last != pfx.first + 1 else 0
  gwid = get_gateway_id(link)
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
        log.error(
          f'Cannot parse {af} prefix {pfx_list[af]} on {link._linkname}\n' + \
            strings.extra_data_printout(f'{ex}') + '\n' + \
            strings.extra_data_printout(f'{link}'),
          log.IncorrectValue,
          'links')
        continue

      if 'allocation' in pfx_list:
        allocation_policy = pfx_list.allocation
      else:
        allocation_policy = get_prefix_IPAM_policy(link,pfx_net,ndict)    # get IPAM policy based on prefix and link size

    if allocation_policy == 'error':                                      # Something went wrong, cannot assing IP addresses
      rq = f'{len(link.interfaces)} nodes'
      if get_gateway_id(link):
        rq = rq + f' plus first-hop gateway'
      hints = []
      if link.type == 'p2p':
        hints = ['Use "type: lan" or a custom pool on links with default gateways']

      log.error(
        f'Cannot use {af} prefix {pfx_list[af]} to address {rq} on {link._linkname}',
        more_data=f'link data: {link}',
        more_hints=hints,
        category=log.IncorrectValue,
        module='links')
      continue

    if not allocation_policy in IPAM_dispatch:
      log.error(
        f'Invalid IP address allocation policy specified in prefix {pfx_list} found on {link._linkname}',
        log.IncorrectValue,
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
        log.error(
          f'Interface ID for node {intf.node} did not result in a usable address on {link._linkname}\n' + \
            strings.extra_data_printout(f'{link}'),
          log.IncorrectType,
          'links')
        continue

      if not '/' in intf[af]:                   # Subnet mask is unknown
        log.error(
          f'Unknown subnet mask for {af} address {intf[af]} used by node {intf.node} on {link._linkname}\n' + \
            strings.extra_data_printout(f'{link}'),
          log.IncorrectType,
          'links')
        continue

"""
Get interface description from interface neighbors
"""
def get_interface_description(node_name: str, intf: Box) -> str:
  ngb_names = [ n.node for n in intf.neighbors ]
  ngb_list  = 'stub' if not ngb_names else ngb_names[0] if len(ngb_names) == 1 else f"[{','.join(ngb_names)}]"
  return f'{node_name} -> {ngb_list}' 

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
set_parent_interface -- set the parent interface and IP address for the IPv4 unnumbered interfaces
"""
def set_parent_interface(ifdata: Box, node: Box) -> None:
  if ifdata.get('ipv4',None) is not True:                         # We're interested only in interfaces that have...
    return                                                        # ... ipv4 set to True

  lbname = node.get('loopback.ifname',None)                       # Try to get the parent interface name
  if lbname:                                                      # Found it, save it in an internal attribute
    ifdata._parent_intf = lbname

  lbipv4 = node.get('loopback.ipv4',None)                         # Try to get the parent IPv4 address
  if lbipv4:                                                      # Save the parent IPv4 address (needed for static routes)
    ifdata._parent_ipv4 = lbipv4

"""
Create node interfaces from link interfaces
"""
def create_node_interfaces(link: Box, addr_pools: Box, ndict: Box, defaults: Box) -> None:
  link_attr_propagate = get_link_propagate_attributes(defaults)

  if log.debug_active('links'):     # pragma: no cover (debugging)
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
                ifdata=data.get_box(value))
    set_interface_name(ifdata,link,intf_cnt)
    set_parent_interface(ifdata,ndict[node])
    ifdata.pop('node',None)                                       # Remove the node name (not needed within the node)
    node_intf = add_node_interface(ndict[node],ifdata,defaults)   # Attach new interface to its node
    value.ifindex = node_intf.ifindex                             # Save ifindex and ifname in link interface data
    value.ifname  = node_intf.ifname                              # ... needed for things like Graph output module that works with links
    interfaces.append({ 'node': node, 'data': node_intf })        # Save newly-created interface for the next step
                                                                  # ... must use dict not Box as Box creates a copy of the data structure

  if log.debug_active('links'):     # pragma: no cover (debugging)
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
      ngh_data = data.get_box({ 'ifname': remote_ifdata.ifname, 'node': remote_node })
      #
      # Find relevant modules that have interface attributes
      mods_with_attr = set([ m for m in ndict[remote_node].get('module',[])
                              if (defaults[m].attributes.get('interface',None) or
                                  defaults[m].attributes.get('link_to_neighbor',None)) and
                                  defaults[m].attributes.get('intf_to_neighbor',True) ])
      #
      # Merge neighbor module data + AF with baseline neighbor data
      ngh_data = interface_data(
                   link=remote_ifdata,
                   link_attr=mods_with_attr.union(['ipv4','ipv6']),
                   ifdata=ngh_data)
      ifdata.neighbors.append(ngh_data)

"""
set_link_loopback_type: when requested, convert stub links to extra loopbacks

This function is called for links that have a single node attached to them. If the device
supports extra loopbacks, and if the 'stub_loopback' parameter is set in the device
or system defailts, the link type is set to loopback.
"""
def set_link_loopback_type(link: Box, nodes: Box, defaults: Box) -> None:
  node = link.interfaces[0].node
  ndata = nodes[node]
  features = devices.get_device_features(ndata,defaults)

  # If we don't know how to create loopbacks on this device, it makes no sense to proceed
  #
  lb_name = devices.get_device_attribute(ndata,'loopback_interface_name',defaults)
  if not lb_name:
    return

  # Check the device feature first, then the system default. Set the link type if the first
  # one you get is True. Also note that a True feature gets translated into Box({}) early
  # in the transformation process (don't ask).
  #
  make_loopback = features.get('stub_loopback',defaults.get('links.stub_loopback',None))
  if make_loopback or isinstance(make_loopback,Box):
    link.type = 'loopback'

"""
Count the number of nodes and hosts on the link. Can be called multiple times
as it checks whether it already did the job before starting the counting process
"""
def count_link_nodes(link: Box, nodes: Box) -> None:
  if 'node_count' in link:                    # Already did a count, we're good  
    return

  node_cnt = len(link.interfaces)             # Set the number of attached nodes
  link['node_count'] = node_cnt

  host_count = 0
  router_count = 0
  for ifdata in link.interfaces:
    ndata = nodes[ifdata.node]
    if ndata.get('role','') == 'host':        # If a device has the 'host' role, it's obviously a host
      host_count = host_count + 1
      if ndata.get('_daemon',False):          # ... but if it is also a daemon, it could also be router
        router_count = router_count + 1
    else:
      router_count = router_count + 1         # ... not a host, must be a router

  if host_count > 0:                          # Remember that we have hosts on the link (so we'll set the default GW)
    link.host_count = host_count

  if router_count > 0:                        # Remember that we have routers (so we won't get stub networks)
    link.router_count = router_count

"""
Get the default link type based on number of nodes. Also used for default pool selection
"""
def get_default_link_type(link: Box) -> str:
  if link.node_count > 2:
    return 'lan'
  
  if link.get('host_count',0):
    return 'lan'
  
  return 'p2p' if link.node_count == 2 else 'stub'

def set_link_type_role(link: Box, pools: Box, nodes: Box, defaults: Box) -> None:
  count_link_nodes(link,nodes)

  if link.node_count == 1:                    # A link with a single node attached to it. Could model it as a loopback
    set_link_loopback_type(link,nodes,defaults)

  # Set the link role to stub if the link has no role, has a single router,
  # is not a VLAN link, and is not a loopback link
  if not 'role' in link and \
     link.get('router_count',0) <= 1 and \
     link.get('type','') != 'loopback' and \
     'vlan_name' not in link:
    link.role = 'stub'

  link.pop('router_count')                    # Temporarily remove the router count

  if link.get('dhcp.subnet.ipv4',None):
    link.host_count = link.get('host_count',0) + 1

  if 'type' not in link:                      # Link type already set, nothing to do
    link.type = get_default_link_type(link)   # Set the link type based on number of attached nodes

def set_link_bridge_name(link: Box, defaults: Box) -> None:
  if link.type in ['p2p','loopback','vlan_member']:                   # No need for bridge names on P2P links, loopbacks and virtual links
    return
  if not 'bridge' in link:
    link['bridge'] = "%s_%d" % (defaults.name[0:10],link.linkindex)   # max 15 chars on Linux
  elif len(link['bridge']) > 15:
    log.error(
      f'Bridge name {link["bridge"]} has more than 15 characters',
      log.IncorrectValue,
      'interfaces')

def check_link_type(data: Box) -> bool:
  node_cnt = data.get('node_count') # link_node_count(data,nodes)
  link_type = data.get('type')

  if 'mtu' in data and not isinstance(data.mtu,int): # pragma: no cover
    log.error(f'MTU parameter should be an integer: {data}',log.IncorrectValue,'links')

  if not link_type: # pragma: no cover (shouldn't get here)
    log.fatal('Internal error: link type still undefined in check_link_type: %s' % data,'links')
    return False

  if node_cnt == 0:
    log.error('No valid nodes on link %s' % data,log.MissingValue,'links')
    return False

  if link_type == 'stub' and node_cnt > 1:
    log.error('More than one node connected to a stub link: %s' % data,log.IncorrectValue,'links')
    return False

  if link_type == 'p2p' and node_cnt != 2:
    log.error('Point-to-point link needs exactly two nodes: %s' % data,log.IncorrectValue,'links')
    return False

  if link_type == 'loopback' and node_cnt != 1:
    log.error(
      f'Loopback link {data._linkname} can have a single node attached\n... {data}',
      log.IncorrectValue,
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
          log.error(
            text=f'Device {ndata.device} does not support unnumbered IPv4 interfaces',
            more_hints=[ f'Used on node {node} interface {ifdata.ifname} (link {ifdata.name})' ],
            category=log.IncorrectValue,
            module='interfaces')
      if 'ipv6' in ifdata:
        if isinstance(ifdata.ipv6,bool) and ifdata.ipv6 and \
            not features.initial.ipv6.lla:
          log.error(
            f'Device {ndata.device} does not support LLA-only IPv6 interfaces used on\n'+
            f'.. node {node} interface {ifdata.ifname} (link {ifdata.name})',
            log.IncorrectValue,
            'interfaces')

'''
copy_link_gateway -- copy link gateway addresses to node-on-link (future interface) data

The link.gateway.ipv4/link.gateway.ipv6 attributes are not copied into
node-on-link data automatically, so we need an extra step after assigning the
link gateway IP (based on gateway.id)

Please note that the link gateway IP has to be propagated only to nodes that use
the gateway module to avoid confusion in configuration templates.
'''
def copy_link_gateway(link: Box, nodes: Box) -> None:
  if 'gateway' not in link:
    return
  for intf in link.interfaces:                              # Copy link gateway into interface attributes
    if 'gateway' not in nodes[intf.node].get('module',[]):  # ... but only for nodes using the gateway module
      continue
    if intf.get('gateway',None) is False:                   # Skip interfaces where gateway is explicitly turned off
      continue
    for af in log.AF_LIST:
      if af in link.gateway:
        intf.gateway[af] = link.gateway[af]

'''
set_default_gateway -- copy link default gateway into host interface data

We're almost done with the link processing. The link data is complete and the
node interfaces have been created. As the last step, we find links that have
host attached and copy link gateway IP address into host interface data -- but
only for the first host interface.

For links without they 'gateway' attribute, we take the IPv4 address of the
first device that is not a host and that does not use DHCP as the link gateway
IPv4 address.

Please note we can't do this step before the node interfaces have been created
because we don't know what the "first interface" is before that.

Finally, while the code might copy 'gateway.ipv6' into interface data if it was
set somewhere else, we don't expect that to be used. IPv6 should use RA.
'''
def set_default_gateway(link: Box, nodes: Box) -> None:
  if not 'host_count' in link:      # No hosts attached to the link, get out
    return
  link.pop('host_count',None)

  # No IPv4 prefix on the link or unnumbered IPv4 link
  if not link.prefix or 'ipv4' not in link.prefix or isinstance(link.prefix.ipv4,bool):
    return

  if log.debug_active('links'):
    print(f'Set DGW for {link}')
  if not 'gateway' in link:                               # Do we have first-hop gateway on the link?
    for ifdata in link.interfaces:                        # Nope, iterate over interfaces, find routers running IPv4
      if nodes[ifdata.node].get('role','') != 'host' and ifdata.get('ipv4',False):
        if ifdata.get('dhcp.client.ipv4',False):
          continue                                        # Skip routers running DHCP clients
        link.gateway.ipv4 = ifdata.ipv4                   # Remember the router's IPv4 address
        if ifdata.ipv4 is not True:                       # ... and if it's not unnumbered
          break                                           # ... get out, we found it

    if link.get('gateway.ipv4',None) is True:             # Did we find an unnumbered IPv4 address?
      log.error(                                          # Complain...
        text=f'Hosts cannot be attached to subnets where all routers have unnumbered interfaces (found in {link._linkname})',
        category=log.IncorrectValue,
        module='links')
      link.pop('gateway',None)                            # ... and remove it, it's useless

  elif link.gateway is False:
    return

  if not 'gateway' in link or not isinstance(link.gateway,Box) or not 'ipv4' in link.gateway: # Didn't find a usable gateway, exit
    if log.debug_active('links'):
      print('... not found')
    return

  if log.debug_active('links'):
    print(f'... DGW: {link.gateway}')

  for ifdata in link.interfaces:                          # Copy link gateway to all hosts attached to the link
    if nodes[ifdata.node].get('role','') == 'host':       # Set gateway only for hosts
      for interface in nodes[ifdata.node].interfaces:     # Find the corresponding host interface
        if link.linkindex == interface.linkindex:
          interface.gateway = link.gateway                # Copy link gateway to host interface

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

'''
Link index utility functions:

* get_next_linkindex: get last linkindex+1 or default value
* get_link_by_index: given a link index, return the link
'''

def get_next_linkindex(topology: Box) -> int:
  if not topology.links:
    topology.links = []
    return topology.defaults.get('link_index',1)

  return topology.links[-1].linkindex + 1

def get_link_by_index(topology: Box, idx: int) -> typing.Optional[Box]:
  for link in topology.links:
    if link.linkindex == idx:
      return link
  return None

'''
set_linknames -- set link name if not defined
'''
def set_linknames(topology: Box) -> None:
  for cnt,link in enumerate(topology.links):
    if link.get('group'):
      link._linkname = f'links[{link.group}]'
    elif not '_linkname' in link:
      link._linkname = f'links[{cnt+1}]'

'''
set_linkindex -- set link index for each link
'''
def set_linkindex(topology: Box) -> None:
  linkindex = topology.defaults.get('link_index',1)
  for link in topology.links:
    link.linkindex = linkindex
    linkindex = linkindex + 1

'''
check_duplicate_address: Check whether any two nodes on the link got duplicate IP
'''
def check_duplicate_address(
      link: Box,
      link_name: typing.Optional[str] = None,
      obj_name: str = 'link',
      module: typing.Optional[str] = None) -> None:

  for af in log.AF_LIST:
    dup_dict = {}
    gw_ip = link.get(f'gateway.{af}',None)
    if isinstance(gw_ip,str):
      dup_dict[gw_ip] = 'gateway'
    for intf in link.interfaces:
      if_ip = intf.get(af,None)
      if not isinstance(if_ip,str):
        continue
      if if_ip in dup_dict:
        link_name = link_name or link._linkname
        log.error(
          f'Duplicate address {if_ip} found on {obj_name} {link_name}: {intf.node} and {dup_dict[if_ip]}',
          category=log.IncorrectValue,
          more_hints=['Set defaults.warnings.duplicate_address to False to disable this check'],
          module=module or obj_name)
      else:
        dup_dict[if_ip] = intf.node

'''
expand_groups -- expand link groups (identified by 'group' and 'members' attributes) into individual links
appended to the end of the link list

This function is called from init_links very early in the topology initialization process
and must do its own data validation.
'''
def expand_groups(topology: Box) -> None:
  for link in list(topology.links):                 # Iterate over existing links (that's why we have to cast it as a list)
    if not 'group' in link:                         # Not a group link, move on
      if 'members' in link:
        log.error(
          f'Link {link._linkname} is not a group link, but has a "members" list',
          log.IncorrectValue,
          'links')
      continue

    try:                                            # Check that the group ID is a valid identifier
      must_be_id(
        parent=link,
        key='group',
        path=link._linkname,
        _abort=True,
        module='links')
    except:                                         # If not, report error and skip the link
      continue

    if not must_be_list(parent=link,key='members',path=link._linkname,create_empty=False,module='links'):
      log.error(                                 # Make sure 'members' is a list
        f'Group link {link._linkname} has no members',
        log.MissingValue,
        'links')
      continue                                      # Report error and skip otherwise

    copy_group_data = data.get_box(link)            # We'll copy all group data into member links
    for key in ['group','members','_linkname']:     # Apart from the link name and 
      copy_group_data.pop(key,None)

    for idx,member in enumerate(link.members):
      member = adjust_link_object(member,f'{link._linkname}[{idx+1}]',topology.nodes)
      member = copy_group_data + member             # Copy group data into member link
      topology.links.append(member)

  # Finally, remove group links from the link list
  topology.links = [ link for link in topology.links if not 'group' in link ]

def links_init(topology: Box) -> None:
  topology.links = adjust_link_list(topology.links,topology.nodes)
  set_linknames(topology)
  expand_groups(topology)
  set_linkindex(topology)

def transform(link_list: typing.Optional[Box], defaults: Box, nodes: Box, pools: Box) -> typing.Optional[Box]:
  if not link_list:
    return None

  for link in link_list:
    set_link_type_role(link=link,pools=pools,nodes=nodes,defaults=defaults)
    if not check_link_type(data=link):
      continue

    set_link_bridge_name(link,defaults)
    link_default_pools = [ get_default_link_type(link) ]
    if 'lan' not in link_default_pools:
      link_default_pools.append('lan')
    assign_link_prefix(link,link_default_pools,pools,nodes,link._linkname)
    copy_link_gateway(link,nodes)
    assign_interface_addresses(link,pools,nodes,defaults)
    create_node_interfaces(link,pools,nodes,defaults=defaults)

    cleanup_link_interface_AF_entries(link)
    if defaults.warnings.duplicate_address:
      check_duplicate_address(link)
    set_default_gateway(link,nodes)

  interface_feature_check(nodes,defaults)
  set_node_af(nodes)
  return link_list

def cleanup(topology: Box) -> None:
  if not 'links' in topology:
    return

#  for link in topology.links:
#    link.pop('_linkname',None)
