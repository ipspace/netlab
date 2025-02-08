from box import Box
from netsim.utils import log

def post_transform(topology: Box) -> None:
  for n in topology.groups.probes.members:
    ndata = topology.nodes[n]
    for intf in ndata.interfaces:
      if intf.get('vlan.trunk'):
        log.warning(text=f'Adding native VLAN 1 to interface {intf.ifname} on node {n}')
        intf.vlan.access_id = 1
        intf.vlan.trunk.untagged = {}
        intf.vlan.native = 'untagged'
        intf.vlan.trunk_id.append(1)
