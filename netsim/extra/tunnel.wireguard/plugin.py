
import ipaddress
import subprocess

from box import Box

from netsim import api
from netsim.augment import devices
from netsim.augment import links as _links
from netsim.augment import nodes as _nodes
from netsim.data import get_box
from netsim.utils import log
from netsim.utils import routing as _routing

from .. import tunnel as _tunnel

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

  Set netlab_linux_packages per node (not device-wide) to install
  wireguard-tools only on nodes with tunnels. The host var replaces the group
  var, so start from the device defaults. Installed during initial config.
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
      if len(intf.neighbors) != 1:
        log.error(
          f'WireGuard tunnel interface should have exactly one neighbor (found {len(intf.neighbors)})',
          more_data=f'node {node} interface {intf.ifname} ({intf.name}) link {get_linkname(topology,intf.linkindex)}',
          module='tunnel.wireguard',
          category=log.IncorrectValue)
        continue

      # Let the shared helper pick the underlay source interface (filtered on
      # tunnel.af when set), then infer the transport AF from the selected
      # interface: prefer IPv4, fall back to IPv6 for IPv6-only underlays.
      u_iflist = _tunnel.get_tunnel_source(ndata,intf,topology)
      if not u_iflist:
        log.error(
          f'Cannot get a tunnel source for link {get_linkname(topology,intf.linkindex)} on node {node}',
          more_data=f'Tunnel source data: {intf.tunnel.source if "tunnel.source" in intf else "none"}',
          category=log.MissingDependency,
          module='tunnel')
        continue

      u_intf = u_iflist[0]
      if 'tunnel.af' not in intf:
        intf.tunnel.af = 'ipv4' if ('ipv4' in u_intf and isinstance(u_intf.ipv4,str)) else 'ipv6'

      src_intf = get_box({
        'ifname': u_intf.ifname,
        'mtu': u_intf.get('mtu',ndata.get('mtu',1500)),
        intf.tunnel.af: str(ipaddress.ip_interface(u_intf[intf.tunnel.af]).ip),
      })
      intf.tunnel._source_intf = src_intf

      # WireGuard devices are ARPHRD_NONE (link/none), so the kernel forces
      # addr_gen_mode to 'none' and never assigns an IPv6 link-local address
      # (random and stable-privacy modes are ignored). OSPFv3 needs one to form
      # adjacencies, so on an IPv6 tunnel we derive a deterministic address from
      # the overlay interface identifier (low 64 bits) -- distinct per endpoint
      # -- for the initial config script to assign when it creates the interface.
      if intf.tunnel.af == 'ipv6':
        intf._ipv6_link_local = _routing.get_ipv6_link_local(intf.ipv6)

      # Default the peer's allowed IPs (the inner/overlay prefixes carried by the
      # tunnel) to a default route per active address family. Use the node's global
      # active AFs, so dual-stack tunnels permit both ranges.
      if 'tunnel.allowed_ips' not in intf:
        af_active = ndata.get('af',{})
        ranges = [ prefix for af,prefix in (('ipv4','0.0.0.0/0'),('ipv6','::/0')) if af_active.get(af) ]
        intf.tunnel.allowed_ips = ','.join(ranges) or '0.0.0.0/0'

      # Derive the WireGuard interface MTU from the underlay source interface
      # MTU minus the encapsulation overhead (80 bytes for an IPv6 underlay,
      # 60 bytes for an IPv4 underlay) so it scales with jumbo-frame underlays.
      if 'mtu' not in intf:
        overhead = 80 if intf.tunnel.af == 'ipv6' else 60
        intf.mtu = src_intf.mtu - overhead

      # Tell the initial config script to create a WireGuard netdev (with an
      # optional IPv6 link-local address) before FRR is configured.
      intf._linux_device_type = 'wireguard'

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
