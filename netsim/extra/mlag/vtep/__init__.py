#
# Plugin to add a shared VTEP loopback to MLAG pairs that use VXLAN
#

from box import Box

from netsim import data
from netsim.augment import addressing, devices, links
from netsim.utils import log
from netsim.utils import routing as _rp_utils

_config_name = 'mlag.vtep'
_requires    = [ 'vxlan', 'lag' ]

POOL_NAME = "mlag_vtep"

def pre_link_transform(topology: Box) -> None:
  global _config_name

  # Error if vxlan/lag module is not loaded
  if 'vxlan' not in topology.module or 'lag' not in topology.module:
    log.error(
      'vxlan and/or lag module is not loaded.',
      log.IncorrectValue,
      _config_name)

  # Find nodes that participate in MLAG and have VXLAN enabled, and add an extra VTEP loopback
  for l in list(topology.get('links',[])):
    if not l.get('lag.mlag.peergroup'):              # Is this an MLAG peerlink?
      continue                                       # Nope - carry on

    # Allocate a shared IP for both peers
    vtep_a : str = ""
    peers = [ i.node for i in l.interfaces ]
    for node_name in peers:
      node = topology.nodes[ node_name ]
      if node.get('lag.mlag.vtep',None) is False:
        continue                                     # Skip nodes for which the plugin is disabled
      if 'vxlan' in node.module:
        af = 'ipv6' if topology.get('vxlan.use_v6_vtep',False) else 'ipv4'
        if not vtep_a:
          pool = node.get('loopback.pool',POOL_NAME)
          prefix = addressing.get(topology.pools, [pool, 'vrf_loopback'])
          if af in prefix:
            vtep_a = prefix[af]
          else:
            log.error(
              f'Loopback pool {pool} does not provide an address for {af} to use as shared VTEP',
              log.MissingValue,
              _config_name)
            return
        vtep_loopback = data.get_empty_box()
        vtep_loopback.type = 'loopback'              # Assign same static IP to both nodes
        vtep_loopback.interfaces = [ { 'node': node_name, af: str(vtep_a) } ]
        vtep_loopback.name = f"MLAG VTEP VXLAN interface shared between {' - '.join(peers)}"
        vtep_loopback.vxlan.vtep = True
        vtep_loopback.linkindex = links.get_next_linkindex(topology)
        topology.links.append(vtep_loopback)
        node.vxlan._shared_vtep = _rp_utils.get_intf_address(vtep_a)

      if log.debug_active('links'):                  # pragma: no cover (debugging)
        print(f'\nmlag.vtep Create VTEP loopback link for {node_name}: {vtep_loopback}')

"""
After the VXLAN module sets the VTEP IP to the shared loopback in module_post_transform, revert the source address back
to the individual loopback address (in case of EVPN, for nodes that support it)
"""
def post_transform(topology: Box) -> None:
  for node,ndata in topology.nodes.items():
    _shared_vtep = ndata.get('vxlan._shared_vtep')
    if not _shared_vtep:
      continue
    if ndata.get('vxlan.flooding','static')!='evpn': # For static VXLAN, keep the shared address
      continue
    features = devices.get_device_features(ndata,topology.defaults)
    if features.get('mlag_vtep.evpn.vtep_source_loopback'):
      af = 'ipv6' if topology.get('vxlan.use_v6_vtep',False) else 'ipv4'
      ndata.vxlan.vtep = _rp_utils.get_intf_address(ndata.loopback[af])
      ndata.vxlan.vtep_interface = ndata.loopback.ifname
