import typing
import netaddr

from box import Box, BoxList
from . import _Module, _dataplane
from .. import data
from ..data import types as _types
from ..utils import log
from ..augment import devices, links

ID_SET = 'lag_id'

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
check_same_pair - Verifies that the given member connects the same pair of nodes as the first
"""
def check_same_pair(first_pair: list[str], member: Box) -> bool:
  others = { n.node for n in member.interfaces if n.node not in first_pair }
  if others:
    log.error(f'All member links must connect the same pair of nodes({first_pair}), found {others}',
      category=log.IncorrectValue,
      module='lag')
    return False
  return True

"""
create_lag_member_links -- expand lag.members for link l and create physical p2p links
"""
def create_lag_member_links(l: Box, topology: Box) -> None:
  is_mlag = l.get('lag.mlag',False) is True                               # Check for mlag bool flag
  if is_mlag:
    if len(l.lag.members)<2:                                              # In case of MLAG, check there are at least 2 members
      log.error(f'MLAG {l._linkname} must have at least 2 member links',
        category=log.IncorrectAttr,
        module='lag')
      return
    l.pop('lag.mlag',None)                                                # Remove from link, put it on M-side interfaces only

  """
  check_mlag_support - check if the given node supports mlag and has the same device type
  """
  def check_mlag_support(node: str, linkname: str, mlag_device: typing.Optional[str]) -> bool:
    _n = topology.nodes[node]
    features = devices.get_device_features(_n,topology.defaults)
    if not features.lag.get('mlag',False):
      log.error(f'Node {_n.name} ({_n.device}) does not support MLAG, cannot be on M-side of LAG {linkname}',
        category=log.IncorrectValue,
        module='lag')
      return False
    elif _n.device != mlag_device:
      log.error(f'Node {_n.name} on MLAG {linkname} has a different device type ({_n.device}) than another M-side node ({mlag_device})',
        category=log.IncorrectValue,
        module='lag')
      return False
    return True

  """
  verify_lag_ifindex - check that selected lag.ifindex does not overlap with any reserved values
  """
  def verify_lag_ifindex(node: str, linkname: str, topology: Box) -> bool:
    _n = topology.nodes[node]
    features = devices.get_device_features(_n,topology.defaults)
    if 'reserved_ifindex_range' in features.lag:                             # Exclude any reserved port channel IDs
      if l.lag.get('ifindex',0) in features.lag.reserved_ifindex_range:
        log.error(f'Selected lag.ifindex({l.lag.ifindex}) for {linkname} overlaps with device specific reserved range ' +
                  f'{features.lag.reserved_ifindex_range} for node {_n.name} ({_n.device})',
          category=log.IncorrectValue,
          module='lag')
        return False
    return True

  """ 
  determine_mlag_sides - figure out which node forms the "1" side of an 1:M MLAG group, and the device type of its M-side peer
  """
  def determine_mlag_sides(member: Box, oneSide: typing.Optional[str]) -> typing.Tuple[typing.Optional[str],typing.Optional[str]]:
    first_pair = [ i.node for i in l.interfaces ]
    maybe_1_side = [ i.node for i in member.interfaces if i.node in first_pair ]
    if oneSide is None:
      if len(maybe_1_side)==1:                    # Is it clear now which node is on the '1' side?
        oneSide = maybe_1_side[0]
      elif len(maybe_1_side)==2:                  # e.g. case of multi-link m-lag [ h1-s1, h1-s1, h1-s2, h1-s2 ]
        return (None,None)                        # Need to see more links before knowing which side is which
    if oneSide in maybe_1_side:
      mSide = [ i.node for i in member.interfaces if i.node!=oneSide ]
      mlag_node = topology.nodes[ mSide[0] ]
      l.interfaces = l.interfaces + [ data.get_box({ 'node': m }) for m in mSide if m not in first_pair ]
      return (oneSide,mlag_node.device)

    log.error(f'Links in MLAG {l.lag.ifindex} must connect exactly 1 node to M other nodes ({l.lag.members})',
      category=log.IncorrectValue,
      module='lag')
    return ("<error>",None)

  l2_ifdata = create_l2_link_base(l,topology)
  mlag_1_side = None                              # Node on the '1' side of MLAG link
  mlag_device = None                              # Device type of the 'M' side
  first_pair = []                                 # Pair of nodes on first link
  for idx,member in enumerate(l.lag.members):
    member = links.adjust_link_object(member,f'{l._linkname}.lag[{idx+1}]',topology.nodes)

    if 'lag' in member:                           # Catch potential sources for inconsistency
      if 'ifindex' not in member.lag:             # ...but allow for custom bond numbering
        log.error(f'LAG attributes must be configured on the link, not member interface {member._linkname}: {member.lag}',
          category=log.IncorrectAttr,
          module='lag')
        return

    if len(member.interfaces)!=2:                 # Check that there are exactly 2 nodes involved
      log.error(f'Link {member._linkname} in LAG {l.lag.ifindex} must have exactly 2 nodes',
        category=log.IncorrectValue,
        module='lag')
      return

    for i in member.interfaces:                   # Check that they all support LAG, and lag.ifindex is not reserved
      if not check_lag_config(i.node,member._linkname,topology):
        return
      if not verify_lag_ifindex(i.node,member._linkname,topology):
        return

    member = l2_ifdata + member                   # Copy L2 data into member link
    member.linkindex = len(topology.links)+1
    member.lag._parentindex = l.linkindex         # Keep track of parent
    if log.debug_active('lag'):
      print(f'LAG create_lag_member_links -> adding link {member}')
    topology.links.append(member)
    if idx==0:                                    # Copy interfaces from first member link
      l.interfaces = [ data.get_box({ 'node': i.node }) for i in member.interfaces ] # no attributes(!)
      first_pair = [ i.node for i in l.interfaces ]
    elif is_mlag:                                 # Figure out which node is on the "1" side starting at 2nd member
      mlag_1_side, mlag_device = determine_mlag_sides(member,mlag_1_side)
      if mlag_1_side=="<error>":
        return
    elif not check_same_pair(first_pair,member):  # Regular LAG: check that it's between the same nodes
      return

  #
  # Post processing - at this point we finally know which is the 1-side node for M-LAG
  #
  if is_mlag:                                     # For MLAG links
    for i in l.interfaces:
      if i.node!=mlag_1_side:
        if not check_mlag_support(i.node,l._linkname,mlag_device):
          return
        i.lag.mlag = True                         # Put 'mlag' flag on M-side (only)
      else:
        if 'ifindex' not in i.lag:                # else assign lag.ifindex if not provided
          _n = topology.nodes[i.node]
          if '_lag_ifindex' in _n:
            lag_ifindex = _n._lag_ifindex
          else:
            lag_ifindex = 1                       # Start at 1
          _n._lag_ifindex = lag_ifindex + 1       # Track next ifindex to assign, per node
          i.lag.ifindex = lag_ifindex             # In time to derive interface name from it

"""
create_peer_links -- creates and configures physical link(s) for given peer link
"""
def create_peer_links(l: Box, topology: Box) -> None:
  """
  check_mlag_peerlink_support - check if the given node supports mlag peerlinks and has the same device type
  """
  def check_mlag_peerlink_support(node: str, linkname: str) -> bool:
    if not check_lag_config(node,linkname,topology):
      return False
    _n = topology.nodes[node]
    features = devices.get_device_features(_n,topology.defaults)
    if not features.lag.get('mlag',False):
      log.error(f'Node {_n.name} ({_n.device}) does not support MLAG, cannot form peerlink {linkname}',
        category=log.IncorrectValue,
        module='lag')
      return False
    return True

  first_pair = []
  l2_ifdata = create_l2_link_base(l,topology)
  for idx,member in enumerate(l.lag.members):
    member = links.adjust_link_object(member,f'{l._linkname}.peerlink[{idx+1}]',topology.nodes)

    if 'lag' in member:                           # Catch potential sources for inconsistency
      log.error(f'LAG attributes must be configured on the link, not peerlink interface {member._linkname}: {member.lag}',
        category=log.IncorrectAttr,
        module='lag')
      return

    if len(member.interfaces)!=2:                 # Check that there are exactly 2 nodes involved
      log.error(f'Peerlink {member._linkname} must have exactly 2 nodes',
        category=log.IncorrectValue,
        module='lag')
      return

    for i in member.interfaces:                   # Check that they all support MLAG peerlinks
      if not check_mlag_peerlink_support(i.node,member._linkname):
        return

    member = l2_ifdata + member                   # Copy L2 data into member link
    if idx==0:                                    # For the first member, use the existing link
      topology.links[l.linkindex-1] = l + member  # Update topology (l is a copy)
      first_pair = [ i.node for i in member.interfaces ]
      _devs = { topology.nodes[n].device for n in first_pair }
      if len(_devs)!=1:                           # Check that both are the same device type
        log.error(f'Nodes {first_pair} on MLAG peerlink {member._linkname} have different device types ({_devs})',
          category=log.IncorrectValue,
          module='lag')
        return
      if log.debug_active('lag'):
        print(f'LAG create_peer_links -> updated first link {l} from {member} -> {topology.links[l.linkindex-1]}')
    else:
      if not check_same_pair(first_pair,member):  # Check that any additional links connect the same nodes
        return
      member.linkindex = len(topology.links)+1
      member.lag._parentindex = l.linkindex       # Keep track of parent
      if log.debug_active('lag'):
        print(f'LAG create_peer_links -> adding link {member}')
      topology.links.append(member)

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

    if l.get('lag.mlag.peergroup',None):          # Turn internal MLAG links into p2p links
      l.type = 'p2p'
      l.prefix = False                            # L2-only
      create_peer_links(l,topology)
    else:
      l.type = 'lag'
      if 'ifindex' not in l.lag:                  # Use user provided lag.ifindex, if any
        l.lag.ifindex = _dataplane.get_next_id(ID_SET)
      create_lag_member_links(l,topology)
    topology.links[l.linkindex-1].lag.pop("members",None)

#
# populate_mlag_peer - Lookup the IPv4 loopback address for the mlag peer, and derive a virtual MAC to use
#
def populate_mlag_peer(node: Box, intf: Box, topology: Box) -> None:
  _n = intf.neighbors[0].node
  peer = topology.nodes[_n]
  features = devices.get_device_features(node,topology.defaults)
  _mlag_peer = features.get('lag.mlag.peer',{})
  if 'ip' in _mlag_peer:
    if 'loopback' in _mlag_peer.ip:
      _ip = peer.get(_mlag_peer.ip,None)
      if _ip:
        intf.lag.mlag.peer = str(netaddr.IPNetwork(_ip).ip)
      else:
        log.error(f'Node {peer.name} must have {_mlag_peer.ip} defined to support MLAG',
          category=log.IncorrectValue,
          module='lag')
    else:
      _net = netaddr.IPNetwork(_mlag_peer.ip)
      _id = 0 if node.id < peer.id else 1
      intf.lag.mlag.peer = str(_net[_id])
      intf.lag.mlag.self = f"{_net[1-_id]}/{_net.prefixlen}"                # including /prefix

  if 'mac' in _mlag_peer:
    _mac = netaddr.EUI(_mlag_peer.mac)                                      # Generate unique virtual MAC per MLAG group
    _mac._set_value(_mac.value + intf.get('lag.mlag.peergroup',0) % 65536 ) # ...based on lag.mlag.peergroup
    intf.lag.mlag.mac = str(_mac)

  for v in ['vlan','ifindex']:
    if v in _mlag_peer:
      intf.lag.mlag[v] = _mlag_peer[v]

class LAG(_Module):

  """
  module_pre_transform -- Add links listed in each lag.members to the topology
  """
  def module_pre_transform(self, topology: Box) -> None:
    if log.debug_active('lag'):
      print(f'LAG module_pre_transform')
    populate_lag_id_set(topology)

    # Expand lag.members into additional p2p links
    process_lag_links(topology)

  """
  After attribute propagation and consolidation, verify that requested features are supported.
  Populate MLAG peer IP and virtual MAC

  Only gets called for nodes with 'lag' module enabled
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)
    for i in node.interfaces:
      if i.get('lag.mlag.peergroup',None):  # Fill in peer loopback IP and vMAC for MLAG peer links
        populate_mlag_peer(node,i,topology)
      elif i.type=='lag':
        i.lag = node.get('lag',{}) + i.lag  # Merge node level settings with interface overrides
        lacp_mode = i.get('lag.lacp_mode')  # Inheritance copying is done elsewhere
        if lacp_mode=='passive' and not features.lag.get('passive',False):
          log.error(f'Node {node.name} does not support passive LACP configured on interface {i.ifname}',
            category=log.IncorrectAttr,
            module='lag',
            hint='lag')

    node.pop('_lag_ifindex',None)           # Cleanup