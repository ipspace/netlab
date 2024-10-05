import typing
import netaddr

from box import Box, BoxList
from . import _Module
from .. import data
from ..utils import log
from ..augment import devices, links

class LAG(_Module):

  """
  link_pre_transform: Process LAG links and add member links to the topology
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    if log.debug_active('lag'):
      print(f'LAG link_pre_transform for {link}')

    # Iterate over links with lag.id, skip over member links we added below
    if 'lag' in link and link.get('type',"")!="p2p":
      if 'members' not in link.lag:
        log.error(
              f'Link {link._linkname} defines "lag.id"={link.lag.id} but no "lag.members"',
              category=log.MissingValue,
              module='lag',
              hint='lag')

      if len(link.interfaces)!=2: # Future: MC-LAG would be 3
        log.error(
            'Current LAG module only supports lags between exactly 2 nodes',
            category=log.IncorrectAttr,
            module='lag',
            hint='lag')

      # 1. Check that the nodes involved all support LAG
      for i in link.interfaces:
        n = topology.nodes[i.node]
        features = devices.get_device_features(n,topology.defaults)
        if 'lag' not in features:
          log.error(
              f'Node {n.name} does not support LAG configured on link {link._linkname}',
              category=log.IncorrectAttr,
              module='lag',
              hint='lag')

      if isinstance(link.lag.members,int):
        count = link.lag.members
        link.lag.members = []
        for i in range(1,count):
          link.lag.members.append( { 'interfaces': link.interfaces + [] } )  # Deep copy

      # 2. Normalize member links list
      link.lag.members = links.adjust_link_list(link.lag.members,topology.nodes,f'lag{link.lag.id}.link[{{link_cnt}}]')

      if log.debug_active('lag'):
        print(f'LAG link_pre_transform after normalizing members: {link}')

      # 3. Check that the nodes in member links match the ones declared for the LAG
      declared = { l.node for l in link.interfaces }
      for m in link.lag.members:
        if any({ l.node not in declared for l in m.interfaces }):
          log.error(
              f'Nodes {m.interfaces} in member link {m._linkname} do not match with LAG {link.lag.id}: {declared}',
              category=log.IncorrectAttr,
              module='lag',
              hint='lag')

        # Add lag ID and append
        m.lag.id = link.lag.id
        m.linkindex = len(topology.links)+1
        m.type = 'p2p'
        m.prefix = False    # Disable IP assignment
        if 'mtu' in link:
          m.mtu = link.mtu  # Copy any MTU setting
        topology.links.append( m )

      link.type = 'lag'
      # Link code marks it as a 'virtual_interface'
