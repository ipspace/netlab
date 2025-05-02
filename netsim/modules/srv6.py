#
# SRv6 transformation module
#
import typing

from box import Box
from ..augment import addressing,devices

from . import _Module
from ..utils import log
from .. import data
import ipaddress
from ..data.global_vars import get_const

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
  for nb in node.get('bgp.neighbors',[]):
    if 'ipv6' not in nb:                               # Skip IPv4-only neighbors
      continue
    for af in DEFAULT_BGP_AF.keys():
      if nb.type=='ebgp':                              # Set next hop unchanged for EBGP peers, to get end-2-end SID routing
        nb._next_hop_unchanged = True
      nb.activate[af] = nb.type in srv6_bgp.get(af,[]) # Configure bgp.activate based on srv6 AF
      if srv6_vpn and nb.type in srv6_vpn.get(af,[]):
        vpn_af = 'vpn'+af.replace('ip','')
        if node.af.get(vpn_af):                        # Check if the VPN AF is enabled
          nb[vpn_af] = nb.ipv6                         # ...and enable it over IPv6 (only)
    if 'ipv4' not in nb and nb.type in (srv6_bgp.get('ipv4',[])+srv6_vpn.get('ipv4',[])):
      nb.ipv4_rfc8950 = True                           # Enable extended next hops when IPv4 AF is used without IPv4 transport


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
    if node.srv6.get('bgp') and 'bgp' not in mods:
      log.error(
          f"Node {node.name} does not have the BGP module enabled to support BGP v4/v6",
          category=log.MissingDependency,
          module='srv6')
    data.bool_to_defaults(node.srv6,'vpn',DEFAULT_BGP_AF)
    if node.srv6.get('vpn') and 'vrf' not in mods:
      log.error(
          f"Node {node.name} does not have the VRF module enabled to support BGP L3VPN",
          category=log.MissingDependency,
          module='srv6')

  def node_post_transform(self, node: Box, topology: Box) -> None:
    mods = node.get('module',[])
    for igp in node.get('srv6.igp',[]): # Check if the IGP module is still active, it may have been removed
      if igp not in mods:
        log.warning(
          text=f"The IGP module for {igp} on node {node.name} has been removed, SRv6 will likely not work",
          module='srv6')
    locator = node.get('srv6.locator')
    if not locator:
       prefix = addressing.get(topology.pools,[get_pool_name()])['ipv6']
       locator = str(prefix)
       node.srv6.locator = locator
    locator_net = ipaddress.IPv6Network(locator)
    if 'ipv6' not in node.loopback:
      log.error(
        f"SRv6 requires an ipv6 loopback address on node {node.name}",
        category=log.MissingValue,
        module='srv6')
    elif ipaddress.IPv6Interface(node.loopback.ipv6).network.subnet_of(locator_net):
      log.error(
        f"Node {node.name} ipv6 loopback address {node.loopback.ipv6} overlaps with locator {locator}",
        category=Warning,
        module='srv6')
    if 'bgp' in node:
      configure_bgp_for_srv6(node,topology)
