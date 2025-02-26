from box import Box
from netsim.utils import log

def post_transform(topology: Box) -> None:
  for n in topology.groups.probes.members:
    ndata = topology.nodes[n]
    for intf in ndata.interfaces:
      if intf.get('vlan.trunk'):
        log.warning(text=f'Adding green VLAN to VLAN trunk interface {intf.ifname} on node {n}')
        intf.vlan.trunk.green = {}
        intf.vlan.trunk_id.append(ndata.vlans.green.id)
