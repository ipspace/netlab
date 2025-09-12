#
# SRv6 transformation module
#
import ipaddress
import typing

from box import Box

from .. import data
from ..augment import addressing, devices
from ..data.global_vars import get_const
from ..utils import log
from . import _Module

# Defaults used for both srv6.bgp and srv6.vpn
DEFAULT_BGP_AF: typing.Final[dict] = {
  'ipv4': [ 'ibgp' ],
  'ipv6': [ 'ibgp' ]
}

"""
Returns the name for the SRv6 locator address pool, default 'srv6_locator'
"""
def get_pool_name() -> str:
  return get_const('srv6.locator_pool.name','srv6_locator')

"""
Configures BGP address families for neighbors, including extended nexthop where needed
"""
def configure_bgp_for_srv6(node: Box, topology: Box) -> None:
  srv6_bgp = node.get('srv6.bgp',{})
  srv6_vpn = node.get('srv6.vpn',{})
  for nb in list(node.get('bgp.neighbors',[])):
    if 'ipv6' not in nb:                               # Skip IPv4-only neighbors
      continue

    for af in DEFAULT_BGP_AF.keys():
      if nb.type in srv6_bgp.get(af,[]) or nb.type in srv6_vpn.get(af,[]):
# If anything, deactivating BGP AFs would break SR-OS and not achieve anything on FRR
#        nb.activate[af] = False                        # Disable regular BGP activation
        pass
      else:
        continue                                       # Skip if neither AF is activated

# The following code is untested and thus commented out
#      if nb.type=='ebgp':                              # Set next hop unchanged for EBGP peers, to get end-2-end SID routing
#        nb.next_hop_unchanged = True
      if af=='ipv4' and 'ipv4' not in nb:
        nb.extended_nexthop = True                     # Enable extended next hops when IPv4 AF is used without IPv4 transport

class SRV6(_Module):
  """
  module_pre_default - create the default SRv6 locator address pool
  """
  def module_pre_default(self, topology: Box) -> None:
    # Defining this as _top addressing includes it in *every* topology
    POOL_NAME = get_pool_name()
    if POOL_NAME not in topology.defaults.addressing:
      topology.defaults.addressing[ POOL_NAME ] = {
        'ipv6': topology.defaults.srv6.locator_pool,
        'prefix6': 48
      }
    elif 'ipv6' not in topology.defaults.addressing[ POOL_NAME ]:
      log.error(
          f"Custom SRv6 addressing pool '{POOL_NAME}' must provide IPv6 prefixes",
          category=log.MissingValue,
          module='srv6')

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    d_features = devices.get_device_features(node,topology.defaults)
    for igp in node.get('srv6.igp',[]):
      if igp not in mods:
        log.error(
          f"Node {node.name} does not have the {igp} IGP module enabled to run SRv6",
          category=log.MissingDependency,
          module='srv6')
      if not d_features.srv6.get(igp):
        log.error(
          f"Node {node.name} (device {node.device}) does not support {igp} as IGP for SRv6",
          category=log.IncorrectValue,
          module='srv6')

    data.bool_to_defaults(node.srv6,'bgp',DEFAULT_BGP_AF)
    if node.srv6.get('bgp'):
      if not d_features.srv6.get('bgp'):
        log.error(
          f"Node {node.name} (device {node.device}) does not support BGP v4/v6 with SRv6",
          category=log.IncorrectValue,
          module='srv6')
      if 'bgp' not in mods:
        log.error(
          f"Node {node.name} does not have the BGP module enabled to support BGP v4/v6",
          category=log.MissingDependency,
          module='srv6')
    data.bool_to_defaults(node.srv6,'vpn',DEFAULT_BGP_AF)    # Typically used with the vrf module, but not only
    if node.srv6.get('vpn') and not d_features.srv6.get('vpn'):
      log.error(
        f"Node {node.name} (device {node.device}) does not support L3VPN BGP v4/v6 with SRv6",
        category=log.IncorrectValue,
        module='srv6')

    locator = node.get('srv6.locator')
    if not locator:
       prefix = addressing.get(topology.pools,[get_pool_name()])['ipv6']
       locator = str(prefix)
       node.srv6.locator = locator
    locator_net = ipaddress.IPv6Network(locator)
    if node.get('srv6.allocate_loopback'):                   # Auto-assign a loopback from locator range
      first_host = next(iter(locator_net.hosts()))           # Use first usable address
      prefix6 = topology.pools['loopback'].get('prefix6',64) # Use loopback.prefix6, default /64
      node.loopback.ipv6 = ipaddress.IPv6Interface((first_host, prefix6)).with_prefixlen

  def node_post_transform(self, node: Box, topology: Box) -> None:
    if 'ipv6' not in node.loopback:
        log.error(
          f"Node {node.name} does not have an IPv6 loopback required for SRv6, and auto-allocation is disabled",
          category=log.MissingValue,
          module='srv6')
    mods = node.get('module',[])
    for igp in node.get('srv6.igp',[]):                      # Check if the IGP module is still active, it may have been removed
      if igp not in mods:
        log.warning(
          text=f"The IGP module for {igp} on node {node.name} has been removed, SRv6 will likely not work",
          module='srv6')
    if 'bgp' in node:
      configure_bgp_for_srv6(node,topology)
