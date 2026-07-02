
import ipaddress
import subprocess
import typing

from box import Box

from netsim import api
from netsim.augment import devices
from netsim.augment import links as _links
from netsim.augment import nodes as _nodes
from netsim.data import get_box
from netsim.utils import log
from netsim.utils import routing as _routing
from netsim.utils import tunnel as _tunnel

_config_name = 'tunnel.wireguard'

def public_key_from_private(private_key: str) -> str:
  '''
  Derive a WireGuard public key from a private key using wireguard-tools
  '''
  try:
    return subprocess.check_output(
      ['wg', 'pubkey'],
      input=f'{private_key}\n',
      text=True,
      stderr=subprocess.DEVNULL).strip()
  except (FileNotFoundError, subprocess.CalledProcessError, OSError):
    log.fatal(
      'Cannot derive WireGuard public key (install wireguard-tools, '
      'or configure tunnel.private_key and tunnel.public_key)',
      module='tunnel.wireguard')

def generate_keypair() -> tuple[str, str]:
  '''
  Generate a WireGuard private/public key pair using wireguard-tools
  '''
  try:
    private_key = subprocess.check_output(
      ['wg', 'genkey'],
      text=True,
      stderr=subprocess.DEVNULL).strip()
    public_key = subprocess.check_output(
      ['wg', 'pubkey'],
      input=f'{private_key}\n',
      text=True,
      stderr=subprocess.DEVNULL).strip()
    return private_key, public_key
  except (FileNotFoundError, subprocess.CalledProcessError, OSError):
    log.fatal(
      'Cannot generate WireGuard keys (install wireguard-tools, '
      'or configure tunnel.private_key and tunnel.public_key)',
      module='tunnel.wireguard')

def ensure_tunnel_keys(
      node: str,
      intf: Box,
      topology: Box) -> None:
  '''
  Ensure tunnel interface data has a matching private/public key pair
  '''
  private_key = intf.tunnel.get('private_key',None)
  public_key = intf.tunnel.get('public_key',None)
  linkname = get_linkname(topology,intf.linkindex)

  if private_key and public_key:
    return

  if public_key and not private_key:
    log.error(
      f'tunnel.public_key without tunnel.private_key on node {node} interface {intf.ifname} ({intf.name})',
      more_data=f'link {linkname}',
      category=log.IncorrectValue,
      module='tunnel.wireguard')
    return

  if private_key:
    intf.tunnel.public_key = public_key_from_private(private_key)
    return

  private_key, public_key = generate_keypair()
  intf.tunnel.private_key = private_key
  intf.tunnel.public_key = public_key
  if log.VERBOSE:
    log.info(
      f'Generated WireGuard key pair for node {node} interface {intf.ifname} ({intf.name})',
      module='tunnel.wireguard')

def add_linux_packages(node: Box, topology: Box) -> None:
  '''
  Add wireguard-tools to the node package list.

  Device group_vars cannot be extended from plugin defaults, so we have to copy
  the device defaults and augment them on nodes using WireGuard tunnels.
  Packages are installed during initial configuration before the management VRF is created.
  '''
  packages = get_box(devices.get_node_group_var(node,'netlab_linux_packages',topology.defaults) or {})
  packages['wireguard-tools'] = 'wg'
  node.netlab_linux_packages = packages

def pre_link_transform(topology: Box) -> None:
  '''
  pre_link_transform hook: set tunnel link type, check whether WireGuard tunnels are P2P
  '''
  _tunnel.set_tunnel_type(topology)
  for link in _tunnel.links(topology,'wireguard'):
    if len(link.interfaces) != 2:
      log.error(
        f'A WireGuard tunnel must have exactly two nodes attached to it (link {link._linkname})',
        category=log.IncorrectAttr,
        module='tunnel.wireguard')

def get_linkname(topology: Box, linkindex: int) -> str:
  '''
  Utility function: get the name of a link referenced in an interface.
  Return 'unknown' when the link cannot be found
  '''
  link = _links.get_link_by_index(topology,linkindex)
  return link._linkname if link is not None else 'unknown'

def _interface_has_af(intf: Box, af: str) -> bool:
  return af in intf and isinstance(intf[af],str)

def _interface_matches_constraints(
      intf: Box,
      t_intf: Box,
      topology: Box) -> bool:
  '''
  Check whether an interface matches the tunnel.source constraints
  (interface type, VRF, link name, and link role) regardless of address family
  '''
  t_vrf  = t_intf.get('tunnel.vrf',None)
  t_type = t_intf.get('tunnel.source.type',None)
  t_name = t_intf.get('tunnel.source.link.name',None)
  t_role = t_intf.get('tunnel.source.link.role',None)

  if t_type is None:
    if intf.type in ['loopback','tunnel']:
      return False
  elif intf.type != t_type:
    return False

  if t_vrf is None:
    if 'vrf' in intf:
      return False
  elif t_vrf != intf.get('vrf',None):
    return False

  if t_name and t_name != intf.get('name',None):
    return False

  if t_role:
    if 'role' in intf:
      if t_role != intf.role:
        return False
    else:
      link = _links.get_link_by_index(topology,intf.linkindex)
      if link is None or t_role != link.get('role',None):
        return False

  return True

def _interface_matches_source(
      intf: Box,
      t_intf: Box,
      topology: Box,
      t_af: str) -> bool:
  return _interface_matches_constraints(intf,t_intf,topology) and _interface_has_af(intf,t_af)

def _source_iflist(ndata: Box, intf: Box) -> list:
  '''
  Return the candidate underlay source interfaces, adding the loopback when the
  tunnel source is pinned to a (global) loopback
  '''
  iflist = ndata.get('interfaces',[])
  if intf.get('tunnel.source.type') == 'loopback' and 'tunnel.vrf' not in intf and 'loopback' in ndata:
    iflist = iflist + [ ndata.loopback ]
  return iflist

def infer_tunnel_af(ndata: Box, intf: Box, topology: Box) -> str:
  '''
  Infer the tunnel transport address family from the candidate underlay
  interfaces. Prefer IPv4 when available (backward compatible), fall back to
  IPv6 for IPv6-only underlays.
  '''
  has_ipv6 = False
  for src_intf in _source_iflist(ndata,intf):
    if not _interface_matches_constraints(src_intf,intf,topology):
      continue
    if _interface_has_af(src_intf,'ipv4'):
      return 'ipv4'
    if _interface_has_af(src_intf,'ipv6'):
      has_ipv6 = True

  return 'ipv6' if has_ipv6 else 'ipv4'

def get_wireguard_source(
      ndata: Box,
      intf: Box,
      topology: Box,
      peer_node: str) -> typing.Optional[Box]:
  '''
  Find the tunnel underlay interface. When the source is not pinned to a
  specific interface, prefer the underlay link connected to the tunnel peer.
  '''
  t_af = intf.get('tunnel.af','ipv4')
  t_source = intf.get('tunnel.source',Box())

  if t_source.get('ifindex') or t_source.get('link.name'):
    return _tunnel.get_tunnel_source(ndata,intf,topology)

  iflist = _source_iflist(ndata,intf)

  peer_match = None
  first_match = None
  for src_intf in iflist:
    if not _interface_matches_source(src_intf,intf,topology,t_af):
      continue

    src_box = get_box({
      'ifname': src_intf.ifname,
      'mtu': src_intf.get('mtu',1500),
      t_af: str(ipaddress.ip_interface(src_intf[t_af]).ip),
    })
    if first_match is None:
      first_match = src_box
    for ngb in src_intf.get('neighbors',[]):
      if ngb.node == peer_node:
        peer_match = src_box
        break

  return peer_match or first_match or _tunnel.get_tunnel_source(ndata,intf,topology)

def wireguard_link_local(intf: Box) -> None:
  '''
  Set an IPv6 link-local address on a WireGuard tunnel interface.

  WireGuard devices are ARPHRD_NONE (link/none), so the kernel forces
  addr_gen_mode to 'none' and never assigns a link-local address (random and
  stable-privacy modes are ignored). OSPFv3 needs one to form adjacencies, so
  we derive a deterministic address that the initial config script assigns when
  the interface is created.
  '''
  if intf.get('tunnel.af') != 'ipv6' or 'ipv6' not in intf:
    return

  if not isinstance(intf.ipv6,str):
    return

  # Reuse the interface identifier (low 64 bits) of the overlay address so the
  # two tunnel endpoints get distinct link-local addresses.
  intf._ipv6_link_local = _routing.get_ipv6_link_local(intf.ipv6)

def post_transform(topology: Box) -> None:
  '''
  post_transform hook: check device support, set tunnel interface source/peer data
  '''
  node_iflist: dict = {}

  # First pass: collect tunnel interfaces and check feature support
  #
  for node,ndata in topology.nodes.items():
    first = True
    node_iflist[node] = []

    for intf in _tunnel.interfaces(ndata,'wireguard'):
      if first:
        first = False
        if not _tunnel.check_feature(ndata,topology,f_name='wireguard',f_desc='WireGuard tunnels'):
          break
        api.node_config(ndata,_config_name)
        add_linux_packages(ndata,topology)

      ensure_tunnel_keys(node,intf,topology)
      node_iflist[node].append(intf)

  if log.get_error_count():
    return

  # Second pass: set defaults and tunnel source
  #
  for node,iflist in node_iflist.items():
    ndata = topology.nodes[node]
    for intf in iflist:
      # Resolve tunnel defaults in code. We cannot rely on schema _default values
      # because those are materialized on the per-node interface entries during
      # link validation (before link->interface propagation) and would then win
      # over an explicit link-level override during the interface merge.
      if 'tunnel.af' not in intf:
        intf.tunnel.af = infer_tunnel_af(ndata,intf,topology)

      if 'tunnel.allowed_ips' not in intf:
        intf.tunnel.allowed_ips = '::/0' if intf.tunnel.af == 'ipv6' else '0.0.0.0/0'

      # Tell the initial config script to create a WireGuard netdev (with an
      # optional IPv6 link-local address) before FRR is configured.
      intf._linux_device_type = 'wireguard'
      wireguard_link_local(intf)

      if len(intf.neighbors) != 1:
        log.error(
          f'WireGuard tunnel interface should have exactly one neighbor (found {len(intf.neighbors)})',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.wireguard',
          category=log.IncorrectValue)
        continue

      ngb = intf.neighbors[0]
      src_intf = get_wireguard_source(ndata,intf,topology,ngb.node)
      if src_intf:
        intf.tunnel._source_intf = src_intf
        # Derive the WireGuard interface MTU from the underlay source interface
        # MTU minus the encapsulation overhead (80 bytes for an IPv6 underlay,
        # 60 bytes for an IPv4 underlay) so it scales with jumbo-frame underlays.
        if 'mtu' not in intf:
          overhead = 80 if intf.tunnel.af == 'ipv6' else 60
          intf.mtu = src_intf.get('mtu',ndata.get('mtu',1500)) - overhead
      else:
        log.error(
          f'Cannot get {intf.tunnel.af} tunnel source for link {get_linkname(topology,intf.linkindex)} on node {node}',
          more_data=f'Tunnel source data: {intf.tunnel.source if "tunnel.source" in intf else "none"}',
          category=log.MissingDependency,
          module='tunnel')
        continue

      if 'name' in intf and '->' in intf.name and 'WireGuard' not in intf.name:
        intf.name += ' [WireGuard tunnel]'

  if log.get_error_count():
    return

  # Third pass: set tunnel peer data after all sources are known
  #
  for node,iflist in node_iflist.items():
    for intf in iflist:
      if len(intf.neighbors) != 1:
        continue

      ngb = intf.neighbors[0]
      ngb_intf = _nodes.get_node_interface(topology.nodes[ngb.node],ifname=ngb.ifname)
      if not ngb_intf:
        log.error(
          f'Internal error: Cannot find the remote tunnel interface for interface {intf.ifname} on {node}',
          category=log.FatalError,
          module='tunnel.wireguard')
        continue
      if 'tunnel._source_intf' not in ngb_intf:
        log.error(
          f'Cannot find tunnel peer endpoint for node {ngb.node}',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.wireguard',
          category=log.MissingDependency)
        continue
      if 'tunnel.public_key' not in ngb_intf:
        log.error(
          f'Missing tunnel.public_key on peer node {ngb.node}',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.wireguard',
          category=log.MissingValue)
        continue
      if 'tunnel.listen_port' not in ngb_intf:
        log.error(
          f'Missing tunnel.listen_port on peer node {ngb.node}',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.wireguard',
          category=log.MissingValue)
        continue

      peer_ip = ngb_intf.tunnel._source_intf[intf.tunnel.af]
      listen_port = ngb_intf.tunnel.listen_port
      if intf.tunnel.af == 'ipv6':
        endpoint = f'[{peer_ip}]:{listen_port}'
      else:
        endpoint = f'{peer_ip}:{listen_port}'

      intf.tunnel._peer = Box({
        'public_key': ngb_intf.tunnel.public_key,
        'endpoint': endpoint,
      })
