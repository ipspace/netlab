import typing
import netaddr

from box import Box
from . import _Module
from .. import data
from ..utils import log
from ..augment import devices

class LAG(_Module):

  """
  link_pre_transform: Copy lag link attributes to interfaces
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
    lag_ifs : typing.List[Box] = [] # Freshly created virtual LAG interfaces to add
    features = devices.get_device_features(node,topology.defaults)
    for i in node.interfaces:
      # 1. Check if the interface is part of a LAG
      if 'lag' in i:

        # If not already, create virtual lag interface on first link in LAG (per node)
        virt_if = [ v for v in lag_ifs if v.lag.id == i.lag.id ]
        if not virt_if:
          if_data = data.get_box(i)
          if_data.ifname = features.lag.if_name.format(**i)
          if_data.ifindex = max([j.ifindex for j in (node.interfaces+lag_ifs)]) + 1
          if_data.links = 1
          if_data.type = 'lag'

          # Remove unwanted data
          for p in ['clab','linkindex','mtu']:
            if_data.pop(p,None)

          # Fix neighbors
          for n in if_data.get('neighbors',{}):
            if 'lag' in n:
              n.ifname = f"lag-{n.lag.id}"
              # TODO check at least one side 'active' in case of LACP

          lag_ifs.append( if_data )
        else:
          virt_if[0].links = virt_if[0].links + 1
          virt_if[0].name = virt_if[0].name + ',' + i.name

        # Remove attributes from physical interface
        for p in list(i.keys()):
          if p not in topology.defaults.lag.attributes.keep_intf:
            i.pop(p,None)

        for n in i.get('neighbors',{}):
          for p in list(n.keys()):
            if p not in topology.defaults.lag.attributes.keep_intf:
              n.pop(p,None)

    node.interfaces.extend( lag_ifs )
