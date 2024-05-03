import netaddr

from box import Box
from . import _Module
from .. import data
from ..utils import log

class LAG(_Module):

  """
  link_pre_transform: Copy link attributes to interfaces
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    if 'lag' in link:
      for i in link.interfaces:
        if 'lag' in i:
          i.lag = link.lag + i.lag
        else:
          i.lag = link.lag

  """
  node_post_transform: Create virtual consolidated 'lag' interfaces for all LAGs, moving L3 attributes
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    log.status_created()
    print("node_post_transform")
    print( node )

    lag_ifs = [] # Freshly created virtual LAG interfaces to add

    for i in node.interfaces:
      # Skip virtual lag interfaces
      if '_lag' in i:
        continue

      # 1. Check if the interface is part of a LAG
      if 'lag' in i:

        # If not already, create virtual lag interface on first link in LAG (per node)
        virt_if = [ v for v in lag_ifs if v._lag == i.lag.id ]
        if not virt_if:
          if_data = data.get_box(i)
          if_data.ifname = f"lag-{i.lag.id}"
          if_data.ifindex = max([j.ifindex for j in (node.interfaces+lag_ifs)]) + 1
          if_data._lag = i.lag.id
          if_data.links = 1
          if_data.type = 'lag'

          # Remove unwanted data
          for p in ['clab','linkindex']:
            if_data.pop(p,None)

          # Fix neighbors
          for n in if_data.get('neighbors',{}):
            if 'lag' in n:
              n.ifname = f"lag-{n.lag.id}"
              # TODO check at least one side 'active' in case of LACP

          # Resolve any MC-LAG peer ids to their loopback IP
          if 'peer' in if_data:
            peers = {}
            for peer in if_data.peer if isinstance(if_data.peer,list) else [if_data.peer]:
               if peer not in topology.get("nodes"):
                 log.error(
                   text=f'{peer} peer for lag on interface {i.name} not found)',
                   category=log.IncorrectValue,
                   module='lag')
                 continue
               p = topology.nodes[peer]

               # TODO: Sanity check that the same lag exists

               peers[p.name] = str(netaddr.IPNetwork(p.loopback.ipv4).ip)
            if_data.peer = peers

          lag_ifs.append( if_data )
        else:
          virt_if[0].links = virt_if[0].links + 1

        # Remove attributes from physical interface
        for p in list(i.keys()):
          if p not in topology.defaults.lag.attributes.keep_intf:
            print( f"Removing '{p}' from {i}" )
            i.pop(p,None)

        for n in i.get('neighbors',{}):
          for p in list(n.keys()):
            if p not in topology.defaults.lag.attributes.keep_intf:
              print( f"Removing '{p}' from neighbor {n}" )
              n.pop(p,None)

    print("Virtual LAG interfaces to be added:")
    print( lag_ifs )
    node.interfaces.extend( lag_ifs )

