import netaddr

from box import Box
from . import _Module
from ..utils import log

class LAG(_Module):

  """
  Node post-transform: Correct ifname and parent_ifname for VLAN interfaces
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    for i in node.interfaces:
      if 'lag' in i:

        # Propagate lacp setting down to each interface
        if 'lacp' not in i.lag:
          i.lag.lacp = node.get('lag.lacp', topology.get('lag.lacp'))

        # resolve peer names to loopback IPs
        if 'peer' in i.lag:
          peers = {}
          for peer in i.lag.peer if isinstance(i.lag.peer,list) else [i.lag.peer]:
             if peer not in topology.get("nodes"):
               log.error(
                 text=f'{peer} peer for lag on interface {i.name} not found)',
                 category=log.IncorrectValue,
                 module='lag')
               continue
             p = topology.nodes[peer]
 
             # TODO: Sanity check that the same lag exists, if LACP then at least 1 side must be active
 
             peers[p.name] = str(netaddr.IPNetwork(p.loopback.ipv4).ip)
          i.lag.peer = peers

      # Fix VLAN parent interface name
      if i.type == 'vlan_member':
          parent_if = node.interfaces[ i.parent_ifindex - 1 ]
          if 'lag' in parent_if:
            lag_id = parent_if.lag.id
            lag_ifname = f"lag-{lag_id}"
            i.ifname = i.ifname.replace( i.parent_ifname, lag_ifname )
            i.parent_ifname = lag_ifname
