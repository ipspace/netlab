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
    vtep_a = None
    peers = [ i.node for i in l.interfaces ]
    for node_name in peers:
      node = topology.nodes[ node_name ]
      if node.get('lag.mlag.vtep',None) is False:
        continue                                    # Skip nodes for which the plugin is disabled
      if 'vxlan' in node.module:
        if not vtep_a:
          pool = node.get('loopback.pool',POOL_NAME)
          vtep_a = addressing.get(topology.pools, [pool, 'vrf_loopback'])['ipv4']
        vtep_loopback = data.get_empty_box()
        vtep_loopback.type = 'loopback'             # Assign same static IP to both nodes
        vtep_loopback.interfaces = [ { 'node': node_name, 'ipv4': str(vtep_a.network_address)+"/32" } ]
        vtep_loopback._linkname = f"MLAG VTEP VXLAN interface shared between {' - '.join(peers)}"
        vtep_loopback.vxlan.vtep = True
        vtep_loopback.linkindex = len(topology.links)+1
        topology.links.append(vtep_loopback)

      if log.debug_active('links'):                 # pragma: no cover (debugging)
        print(f'\nmlag.vtep Create VTEP loopback link for {node_name}: {vtep_loopback}')

#
# post_transform: Copy IGP configuration from primary loopbacks to VTEP loopbacks
#
def post_transform(topology: Box) -> None:
  for node in topology.nodes.values():              # For each node
    if not node.get('vxlan.vtep'):
      continue
    lb = node.get('loopback',{})
    for intf in node.interfaces:
      if intf.type != 'loopback' or not intf.get('vxlan.vtep'):
        continue
      for igp in ['isis','ospf','eigrp','ripv2']:   # Copy IGP from primary loopback
        if igp in lb:
          intf[igp] = lb[igp]