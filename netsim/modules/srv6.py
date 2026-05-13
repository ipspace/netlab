#
# SRv6 transformation module
#
import typing

from box import Box

from .. import data
from ..augment import addressing, devices
from ..data import validate
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
  srv6 = node.get('srv6',{})
  if not srv6:
    return

  for nb in node.get('bgp.neighbors',[]):
    if 'ipv6' not in nb:                                # Skip IPv4-only neighbors
      continue

    ngb_node = topology.nodes[nb.name]                  # Get neighbor node data
    if 'srv6' not in ngb_node.get('module',[]):         # Is neighbor running SRv6?
      continue                                          # No? Too bad, let's not bother them

    need_srv6 = False
    for svc in ['bgp','vpn']:                           # Iterate over potential SRv6 services
      srv6_svc = srv6.get(svc,{})                       # Get service definition for this node
      for af in DEFAULT_BGP_AF.keys():                  # Next, iterate over address families for this service
        svc_ngb_type = srv6_svc.get(af,[])              # ... get neighbor type for this svc/af combo
        if nb.type not in svc_ngb_type:                 # ... and check whether this neighbor matches
          continue                                      # It doesn't? Meh, better luck next time

        data.append_to_list(nb.srv6,svc,af)             # Adjust neighbor data
        need_srv6 = True                                # ... and remember we need SRv6
        if af=='ipv4':                                  # IPv4 service over SRv6?
          nb.extended_nexthop = True                    # ... needs extended next hop capability

    if not need_srv6:                                   # No SRv6 for this neighbor?
      continue                                          # ... cool, let's get out of here

    if nb.type == 'ebgp':                               # Are we running SRv6 services with EBGP neighbor?
      nb.srv6.next_hop_unchanged = True                 # Cool, but we have to take care of next hops


class SRV6(_Module):
  """
  module_pre_default - create the default SRv6 locator address pool
  """
  def module_pre_default(self, topology: Box) -> None:
    if 'srv6' in topology:
      validate.legacy_attributes(
        t_object=topology,
        topology=topology,
        o_path=f'',
        module='srv6',
        attr_namespace='global')

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

  def module_pre_transform(self, topology: Box) -> None:
    addressing.get(topology.pools,[get_pool_name()])                  # Throw away the all-zeroes prefix

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if 'srv6' in node:
      validate.legacy_attributes(
        t_object=node,
        topology=topology,
        o_path=f'nodes.{node.name}',
        module='srv6',
        attr_namespace='node')

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
