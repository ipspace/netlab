import typing
import netaddr

from box import Box, BoxList
from . import _Module, _dataplane
from .. import data
from ..data import types as _types
from ..utils import log
from ..augment import devices, links

ID_SET = 'lag_id'
PEERLINK_ID_SET = 'peerlink_id'

PEERLINK_ID_ATT = 'lag.mlag.peergroup'

"""
populate_lag_id_set -- Collect any user defined lag.ifindex values globally and initialize ID generator
"""
def populate_lag_id_set(topology: Box) -> None:
  _dataplane.create_id_set(ID_SET)
  # Note that 0 is a valid lag.ifindex value
  LAG_IDS = { l.lag.ifindex for l in topology.links
                if isinstance(l.get('lag.ifindex',None),int) }
  _dataplane.extend_id_set(ID_SET,LAG_IDS)
  _dataplane.set_id_counter(ID_SET,topology.defaults.lag.start_lag_id,100)

"""
populate_peerlink_id_set -- Collect any user defined lag.mlag.peergroup values globally and initialize ID generator
"""
def populate_peerlink_id_set(topology: Box) -> None:
  _dataplane.create_id_set(PEERLINK_ID_SET)
  PEERLINK_IDS = { l[PEERLINK_ID_ATT] for l in topology.links
                   if not isinstance(l.get(PEERLINK_ID_ATT,False),bool) }
  _dataplane.extend_id_set(PEERLINK_ID_SET,PEERLINK_IDS)
  _dataplane.set_id_counter(PEERLINK_ID_SET,1,256)

"""
create_l2_link_base - Create a L2 P2P link as base for member links
"""
def create_l2_link_base(l: Box, topology: Box) -> Box:
  l2_ifdata = data.get_box({ 'type': "p2p", 'prefix': False, 'lag': {} }) # Construct an L2 member link
  for a in list(topology.defaults.lag.attributes.lag_l2_ifattr):
    if a in l:
      l2_ifdata[a] = l[a]
  return l2_ifdata

"""
check_lag_config - check if the given node supports lag and has the module enabled
"""
def check_lag_config(node: str, linkname: str, topology: Box) -> bool:
  _n = topology.nodes[node]
  features = devices.get_device_features(_n,topology.defaults)
  if 'lag' not in features:
    log.error(f'Node {_n.name} ({_n.device}) does not support lag module, cannot be part of LAG {linkname}',
      category=log.IncorrectAttr,
      module='lag')
    return False
  if 'lag' not in _n.get('module',[]):
    log.error(f'lag module not enabled for node {_n.name}, cannot be part of LAG {linkname}',
      category=log.IncorrectAttr,
      module='lag')
    return False
  return True

"""
check_mlag_support - check if the given node supports mlag
"""
def check_mlag_support(node: str, linkname: str, topology: Box) -> bool:
  _n = topology.nodes[node]
  features = devices.get_device_features(_n,topology.defaults)
  if not features.lag.get('mlag',False):
    log.error(f'Node {_n.name} ({_n.device}) does not support MLAG, cannot be part of peerlink or M-side of LAG {linkname}',
      category=log.IncorrectValue,
      module='lag')
    return False
  return True

"""
normalized_members - builds a normalized list of lag member links, checking various conditions
"""
def normalized_members(l: Box, topology: Box, peerlink: bool = False) -> list:
  members = []                                      # Build normalized list of members
  _name = "peerlink" if peerlink else "lag"
  for idx,member in enumerate(l.lag.members):
    member = links.adjust_link_object(member,f'{l._linkname}.{_name}[{idx+1}]',topology.nodes)
    if 'lag' in member:                             # Catch potential sources for inconsistency
      lag_atts = len(member.lag) - (1 if 'ifindex' in member.lag else 0)
      if peerlink or (lag_atts>0):                  # ...but allow for custom bond numbering
        log.error(f'LAG attributes must be configured on the link, not member interface {member._linkname}: {member.lag}',
                  category=log.IncorrectAttr,
                  module='lag')
        return []
    if len(member.interfaces)!=2:                   # Check that there are exactly 2 nodes involved
      log.error(f'Link {member._linkname} in LAG {l.lag.ifindex} must have exactly 2 nodes',
                category=log.IncorrectValue,
                module='lag')
      return []
    if member.interfaces[0].node==member.interfaces[1].node:
      log.error(f'Link {member._linkname} in LAG {l.lag.ifindex} cannot connect a node to itself',
                category=log.IncorrectValue,
                module='lag')
      return []
    members.append(member)
  return members

"""
set_lag_ifindex - Assign lag.ifindex, check for overlap with any reserved values
"""
def set_lag_ifindex(laglink: Box, intf: Box, is_mside: bool, topology: Box) -> bool:
  intf_lag_ifindex = intf.get('lag.ifindex',None)              # Use user provided lag.ifindex, if any
  link_lag_ifindex = laglink.get('lag.ifindex',None)
  _n = topology.nodes[intf.node]
  next_ifindex = _n.get('_lag_ifindex',None)
  if intf_lag_ifindex is None:
    if link_lag_ifindex is None:
      if is_mside:                                             # For M: side we need matching lag.ifindex
        if next_ifindex is None:                               # Do we have a local preference?
          next_ifindex = _dataplane.get_next_id(ID_SET)        # No -> allocate globally
        laglink.lag.ifindex = link_lag_ifindex = next_ifindex  # Put on the link for the other M side to match
      else:
        if next_ifindex is None:
          next_ifindex = topology.defaults.lag.start_lag_id    # Start at start_lag_id (default 1)
        link_lag_ifindex = next_ifindex
        intf.lag.ifindex = link_lag_ifindex                    # Put it on the interface for bond naming
    elif next_ifindex and next_ifindex>link_lag_ifindex:
      link_lag_ifindex = next_ifindex                          # Cannot accept link level lag.ifindex
      if is_mside:
        laglink.lag.ifindex = next_ifindex                     # Override the unacceptable link value
    _n._lag_ifindex = link_lag_ifindex + 1                     # Track next ifindex to assign, per node
    intf_lag_ifindex = link_lag_ifindex
  elif link_lag_ifindex is None:
    laglink.lag.ifindex = link_lag_ifindex = intf_lag_ifindex

  features = devices.get_device_features(_n,topology.defaults)
  if 'reserved_ifindex_range' in features.lag:                 # Exclude any reserved port channel IDs
    if intf_lag_ifindex in features.lag.reserved_ifindex_range:
      log.error(f'Selected lag.ifindex({intf_lag_ifindex}) on {laglink._linkname} overlaps with device specific reserved range ' +
                f'{features.lag.reserved_ifindex_range} for node {_n.name} ({_n.device})',
        category=log.IncorrectValue,
        module='lag')
      return False
  return True

"""
split_dual_mlag_link - Split dual-mlag pairs into 2 lag link groups, returns the new link
"""
def split_dual_mlag_link(link: Box, topology: Box) -> Box:
  def no_peer(i: Box) -> Box:
    i.pop('_peer',None)                                  # Remove internal _peer attribute
    return i    
      
  split_copy = data.get_box(link)                        # Make a copy
  split_copy.linkindex = len(topology.links)+1           # Update its link index
  split_copy._linkname = split_copy._linkname + "-2"     # Assign unique name
  split_copy.lag.pop('members',None)                     # Clean up members
  first_pair = ( link.interfaces[0].node, link.interfaces[0]._peer )
  split_copy.interfaces = [ no_peer(i) for i in link.interfaces if i.node in first_pair ]
  topology.links[link.linkindex-1].interfaces = [ no_peer(i) for i in link.interfaces if i.node not in first_pair ]
  if log.debug_active('lag'):
    print(f'LAG split_dual_mlag_links -> adding split link {split_copy}')
    print(f'LAG split_dual_mlag_links -> remaining link {topology.links[link.linkindex-1]}')
  topology.links.append(split_copy)
  return split_copy

"""
create_lag_member_links -- expand lag.members for link l and create physical p2p links
"""
def create_lag_member_links(l: Box, topology: Box) -> None:

  """
  analyze_lag - figure out which type of LAG we're dealing with:
                 1. A 2-node regular lag
                 2. A 1:2 node mlag (3 nodes total)
                 3. A 2:2 node dual mlag (4 nodes total)

                 Returns updated node_count set, bool is_mlag, bool dual_mlag, string one_side
  """
  def analyze_lag(members: list, node_count: dict) -> typing.Tuple[bool,bool,str]:
    for m in members:
      for i in m.interfaces:
       if i.node in node_count:
         node_count[ i.node ] = node_count[ i.node ] + 1
       else:
         node_count[ i.node ] = 1
 
    if len(node_count)==2:                                 # Regular LAG between 2 nodes
      return (False,False,"")
    elif len(node_count)==3:                               # 1:2 MLAG or weird MLAG triangle
      for node_name,count in node_count.items():
        if count==len(members):
          return (True,False,node_name)                    # Found the 1-side node
    elif len(node_count)==4:                               # 2:2 dual MLAG
      return (True,True,"")

    log.error(f'Unsupported configuration of {len(node_count)} nodes on LAG {l.lag.ifindex}, must consist of ' +
               'either 2, 3 or 4 different nodes connected as 1:1, 1:2 or 2:2',
              category=log.IncorrectValue,
              module='lag')
    return (False,False,"<error>")

  members = normalized_members(l,topology)        # Build list of normalized member links
  if not members:
    return
  node_count: typing.Dict[str,int] = {}           # Count how many times nodes are used
  is_mlag, dual_mlag, one_side = analyze_lag(members,node_count)
  if one_side=="<error>":                         # Check for errors
    return

  l.interfaces = []                               # Build interface list for lag link
  skip_atts = list(topology.defaults.lag.attributes.lag_no_propagate)
  for node in node_count:
    ifatts = data.get_box({ 'node': node })
    for m in members:                             # Collect attributes from member links
      if node in [ i.node for i in m.interfaces ]:# ...in which <node> is involved
        ifatts = ifatts + { k:v for k,v in m.items() if k not in skip_atts }
        if dual_mlag:
          ifatts._peer = [ i.node for i in m.interfaces if i.node!=node ][0]
    is_mside = is_mlag and node!=one_side         # Set flag if this node is the M: side
    if not set_lag_ifindex(l,ifatts,is_mside,topology):
      return
    if node==one_side:
      if not check_lag_config(node,l._linkname,topology):
        return
    elif is_mlag:
      if not check_mlag_support(node,l._linkname,topology):
        return
      ifatts.lag._mlag = True                     # Set internal flag

    if log.debug_active('lag'):
      print(f'LAG create_lag_member_links for node {node} -> collected ifatts {ifatts}')
    l.interfaces.append( ifatts )

  _sl = split_dual_mlag_link(l,topology) if dual_mlag else None
  split_nodes = [ i.node for i in _sl.interfaces ] if _sl else []

  l2_ifdata = create_l2_link_base(l,topology)
  keep_attr = list(topology.defaults.lag.attributes.lag_member_ifattr)
  for member in members:
    member = l2_ifdata + member                   # Copy L2 data into member link
    member = data.get_box({ k:v for k,v in member.items() if k in keep_attr }) # Filter out things not needed
    member.linkindex = len(topology.links)+1
    parent = _sl if _sl and member.interfaces[0].node in split_nodes else l
    member.lag._parentindex = parent.linkindex    # Keep track of parent
    if log.debug_active('lag'):
      print(f'LAG create_lag_member_links -> adding link {member}')
    topology.links.append(member)

"""
create_peer_links -- creates and configures physical link(s) for given peer link
"""
def create_peer_links(l: Box, topology: Box) -> bool:

  """
  check_same_pair - Verifies that the given member connects the same pair of nodes as the first
  """
  first_pair : typing.List[str] = []
  def check_same_pair(member: Box) -> bool:
    others = { n.node for n in member.interfaces if n.node not in first_pair }
    if others:
      log.error(f'All member links must connect the same pair of nodes({first_pair}), found {others}',
        category=log.IncorrectValue,
        module='lag')
      return False
    return True

  members = normalized_members(l,topology,peerlink=True)
  l2_ifdata = create_l2_link_base(l,topology)

  for idx,member in enumerate(members):
    member = l2_ifdata + member                   # Copy L2 data into member link
    if idx==0:                                    # For the first member, use the existing link
      topology.links[l.linkindex-1] = l + member  # Update topology (l is a copy)
      first_pair = [ i.node for i in member.interfaces ]
      _devs = { topology.nodes[n].device for n in first_pair }
      if len(_devs)!=1:                           # Check that both are the same device type
        log.error(f'Nodes {first_pair} on MLAG peerlink {member._linkname} have different device types ({_devs})',
          category=log.IncorrectValue,
          module='lag')
        return False
      for node in first_pair:
        if not check_mlag_support(node,l._linkname,topology):
          return False
      if log.debug_active('lag'):
        print(f'LAG create_peer_links -> updated first link {l} from {member} -> {topology.links[l.linkindex-1]}')
    else:
      if not check_same_pair(member):             # Check that any additional links connect the same nodes
        return False
      member.linkindex = len(topology.links)+1
      member.lag._parentindex = l.linkindex       # Keep track of parent
      if log.debug_active('lag'):
        print(f'LAG create_peer_links -> adding link {member}')
      topology.links.append(member)
  
  return True

"""
process_lag_links - process all links with 'lag' attribute
"""
def process_lag_links(topology: Box) -> None:
  for l in list(topology.links):                   # Make a copy of the list, gets modified
    if 'lag' not in l:
      continue
    elif not 'members' in l.lag:
      log.error(f'must define "lag.members" on LAG link {l._linkname}',
        category=log.IncorrectAttr,
        module='lag')
      continue
    elif not _types.must_be_list(parent=l.lag,key='members',path=l._linkname,module='lag'):
      continue

    peerlink_id = l.get(PEERLINK_ID_ATT,None)      # Turn internal MLAG links into p2p links
    if peerlink_id:
      if peerlink_id is True:                      # Auto-assign peerlink ID if requested
        l[PEERLINK_ID_ATT] = _dataplane.get_next_id(PEERLINK_ID_SET)
      l.type = 'p2p'
      l.prefix = False                             # L2-only
      if not create_peer_links(l,topology):        # Check for errors
        return
    else:
      l.type = 'lag'
      create_lag_member_links(l,topology)
    topology.links[l.linkindex-1].lag.pop("members",None)

#
# populate_mlag_peer - Lookup the IPv4 loopback address for the mlag peer, and derive a virtual MAC to use
#
def populate_mlag_peer(node: Box, intf: Box, topology: Box) -> None:
  peer = topology.nodes[intf.neighbors[0].node]
  features = devices.get_device_features(node,topology.defaults)
  mlag_peer = features.get('lag.mlag.peer',{})
  _target = node.lag if mlag_peer.get('global',False) else intf.lag         # Set at node or intf level?
  if 'ip' in mlag_peer:
    if mlag_peer.ip == 'linklocal':
      _target.mlag.peer = 'linklocal'
    elif 'loopback' in mlag_peer.ip:                                        # Could check if an IGP is configured
      ip = peer.get(mlag_peer.ip,None)
      if ip:
        _target.mlag.peer = str(netaddr.IPNetwork(ip).ip)
      else:
        log.error(f'Node {peer.name} must have {mlag_peer.ip} defined to support MLAG',
          category=log.IncorrectValue,
          module='lag')
    else:
      net = netaddr.IPNetwork(mlag_peer.ip)
      id = 0 if node.id < peer.id else 1
      _target.mlag.peer = str(net[1-id])                                    # Higher node ID gets .1
      _target.mlag.self = f"{net[id]}/{net.prefixlen}"                      # including /prefix

  if 'backup_ip' in mlag_peer:
    bk_ip = peer.get(mlag_peer.backup_ip,None)
    if bk_ip:
      _target.mlag.peer_backup_ip = str(netaddr.IPNetwork(bk_ip).ip)
    else:
      log.error(f'Node {peer.name} must have "{mlag_peer.backup_ip}" defined to support backup MLAG peerlink',
                category=log.IncorrectValue,
                module='lag')

  if 'mac' in mlag_peer and not isinstance(_target.get('mlag.mac',None),str):
    mac = netaddr.EUI(mlag_peer.mac)                                        # Generate unique virtual MAC per MLAG group
    mac._set_value(mac.value + intf.get(PEERLINK_ID_ATT,0) % 65536 )        # ...based on lag.mlag.peergroup
    _target.mlag.mac = str(mac)

  for v in ['vlan','ifindex']:
    if v in mlag_peer:
      _target.mlag[v] = mlag_peer[v]
  
  intf.pop('vlan',None)                                                     # Remove any VLANs provisioned on peerlinks

class LAG(_Module):

  """
  module_pre_transform -- Add links listed in each lag.members to the topology
  """
  def module_pre_transform(self, topology: Box) -> None:
    if log.debug_active('lag'):
      print(f'LAG module_pre_transform')
    populate_lag_id_set(topology)
    populate_peerlink_id_set(topology)

    process_lag_links(topology)             # Expand lag.members into additional p2p links

  """
  After attribute propagation and consolidation, verify that requested features are supported.
  Populate MLAG peer IP and virtual MAC

  Only gets called for nodes with 'lag' module enabled
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)
    has_peerlink = False
    uses_mlag = False
    for i in node.interfaces:
      if i.get(PEERLINK_ID_ATT,None):       # Fill in peer loopback IP and vMAC for MLAG peer links
        populate_mlag_peer(node,i,topology)
        has_peerlink = True
      elif i.type=='lag':
        node_atts = { k:v for k,v in node.get('lag',{}).items() if k!='mlag'}
        i.lag = node_atts + i.lag           # Merge node level settings with interface overrides
        # i.pop('mtu',None)                 # Next PR: Remove any MTU settings - inherited from members

        if 'mode' in i.lag:
          log.error(f'lag.mode {i.lag.mode} used by node {node.name} is deprecated, use only 802.3ad',
            category=Warning,
            module='lag')
          if i.lag.mode!='802.3ad':
            i.lag.lacp = 'off'              # Disable LACP for other modes

        lacp_mode = i.get('lag.lacp_mode')
        if lacp_mode=='passive' and not features.lag.get('passive',False):
          log.error(f'Node {node.name}({node.device}) does not support passive LACP configured on interface {i.ifname}',
            category=log.IncorrectAttr,
            module='lag')
        if i.lag.get('_mlag',False) is True:
          uses_mlag = True
          if 'ipv4' in i or 'ipv6' in i:
            log.error(f'Node {node.name}: IP address directly on MLAG interface {i.ifname} is not supported, use a VLAN instead',
              category=log.IncorrectAttr,
              module='lag')
    
    if uses_mlag and not has_peerlink:
      log.error(f'Node {node.name} uses MLAG but has no peerlink (lag with {PEERLINK_ID_ATT}) configured',
        category=log.IncorrectAttr,
        module='lag')

    node.pop('_lag_ifindex',None)           # Cleanup
