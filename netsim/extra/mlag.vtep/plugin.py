#
# Plugin to add a shared VTEP loopback to MLAG pairs that use VXLAN
#

from netsim.utils import log
from netsim.augment import addressing
from netsim import data
from box import Box

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
    if not l.get('lag.mlag.peergroup'):             # Is this an MLAG peerlink?
      continue                                      # Nope - carry on

    # Allocate a shared IP for both peers
    vtep_a = addressing.get(topology.pools, [POOL_NAME, 'vrf_loopback'])['ipv4']
    peers = [ i.node for i in l.interfaces ]
    for node_name in peers:
      node = topology.nodes[ node_name ]
      if node.get('lag.mlag.vtep',None) is False:
        continue                                    # Skip nodes for which the plugin is disabled
      if 'vxlan' in node.module:
          vtep_loopback = data.get_empty_box()
          vtep_loopback.type = 'loopback'           # Assign same static IP to both nodes
          vtep_loopback.interfaces = [ { 'node': node_name, 'ipv4': str(vtep_a.network_address)+"/32" } ]
          vtep_loopback._linkname = f"MLAG VTEP VXLAN interface shared between {' - '.join(peers)}"
          vtep_loopback.vxlan.vtep = True
          topology.links.append(vtep_loopback)

      if log.debug_active('links'):                 # pragma: no cover (debugging)
        print(f'\nmlag.vtep Create VTEP loopback link for {node_name}: {vtep_loopback}')
