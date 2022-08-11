import typing

from . import _Module
from box import Box
from .. import common

class EVPN(_Module):

  """
  Node pre-transform: set evpn.use_ibgp node attribute based on global setting
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    use_ibgp = topology.evpn.get("use_ibgp",None)
    node.evpn.use_ibgp = use_ibgp if isinstance(use_ibgp,bool) else topology.defaults.evpn.get("use_ibgp",True)

  """
  Node post-transform: runs after VXLAN module

  Add 'evi' attribute (EVPN Instance) to VLANs that have a 'vni' attribute
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    if node.get('vxlan') and node.vxlan.vlans:
      for vname in node.vxlan.vlans:
        if not 'evpn' in node.vlans[vname] or not 'evi' in node.vlans[vname].evpn:
          # Default EVI range : 1..65535 (16 bit)
          node.vlans[vname].evpn.evi = node.vlans[vname].id # Set equal to VLAN id
        elif node.vlans[vname].evpn.evi < 1 or node.vlans[vname].evpn.evi > 65535:
          common.error(
            f'Invalid vlan.evi value {node.vlans[vname].evi} for VLAN {vname}',
            common.IncorrectValue,
            'evpn')
