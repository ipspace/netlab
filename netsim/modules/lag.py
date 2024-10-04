import typing
import netaddr

from box import Box
from . import _Module
from .. import data
from ..utils import log
from ..augment import devices

#
# Checks if 2 lists have the same elements, independent of order
#
def same_list(l1,l2):
  for l in l1:
    if l not in l2:
      return False
  return len(l1)==len(l2)

class LAG(_Module):

  """
  link_pre_transform: Create virtual LAG links
  """
  def link_pre_transform(self, link: Box, topology: Box) -> None:
    if log.debug_active('vlan'):
      print(f'LAG link_pre_transform for {link}')
    if 'lag' in link and link.get('type',"")!="lag":

      # Lookup virtual LAG link with same id between same pair of nodes, create if not existing
      vlag = None
      for l in topology.links:
        if 'lag' in l and l.get('type',"")=="lag" and l.lag.id == link.lag.id \
            and same_list(l.interfaces,link.interfaces):
          vlag = l
          break
      
      if vlag is None:
        vlag = data.get_box(link)
        vlag.type = "lag"
        vlag.linkindex = len(topology.links) + 1
        vlag._linkname = f"links[{vlag.linkindex}]"
        vlag.interfaces = [ i for i in link.interfaces ] # Make a deep copy
        vlag.pop('mtu',None)                             # Remove any MTU attribute
        topology.links.append(vlag)

        if log.debug_active('vlan'):
          print(f'LAG link_pre_transform created virtual link: {vlag}')

        # remove any VLAN attributes from original link
        link.pop('vlan',None)

  """
  node_post_transform: Check for correct supported configuration of LAG
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)
    for i in node.interfaces:
      # 1. Check if the interface is part of a LAG
      if 'lag' in i:
        if 'lag' not in features:
          log.error(
              f'Node {node.name} does not support LAG configured on {i.ifname}',
              category=log.IncorrectAttr,
              module='lag',
              hint='lag')

        _type = i.get("type")
        if _type=="lag":
          continue
        elif _type!="p2p":
          log.error(
              f'Node {node.name} has a LAG configured on {i.ifname} which is not a p2p link ({_type})',
              category=log.IncorrectAttr,
              module='lag',
              hint='lag')
