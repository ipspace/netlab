import typing

from . import _Module,_routing
from box import Box
from .. import common
from .. import data

class EVPN(_Module):

  def module_init(self, topology: Box) -> None:
    topology.defaults.vxlan.flooding = 'evpn'

  """
  Node pre-transform:
  """
  def node_pre_transform(self, node: Box, topology: Box) -> None:
    pass

  """
  Node post-transform: runs after VXLAN module

  Add 'evi' (EVPN Instance),'rd' and 'rt' attributes to VLANs that have a 'vni' attribute
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:

    # evpn.use_ibgp was the old way of saying 'run EVPN over IBGP'
    #
    # This parameter has been replaced with evpn.session parameter and will eventually
    # disappear. In the meantime, 'evpn.use_ibgp' results in 'evpn.session' being
    # set to 'ibgp'
    if 'evpn' in node and 'use_ibgp' in node.evpn:
      data.must_be_bool(
        node,'evpn.use_ibgp',f'nodes.{node.name}.evpn.use_ibgp',
        module='evpn')
      node.evpn.session = ['ibgp'] if node.evpn.use_ibgp else ['ebgp']

    bgp_session = data.get_from_box(node,'evpn.session') or []

    vlan_list = data.get_from_box(node,'vxlan.vlans') or []       # Get the list of VXLAN-enabled VLANs
    if not vlan_list:
      return                                                      # This could be a route reflector running EVPN

    # Enable EVPN AF on all BGP neighbors with the correct session type
    # that also use EVPN module
    #
    for bn in node.bgp.get('neighbors',[]):
      if bn.type in bgp_session and 'evpn' in topology.nodes[bn.name].get('module'):
        bn.evpn = True

    rid = None
    for vname in vlan_list:
      evpn  = node.vlans[vname].evpn
      epath = f'nodes.{node.name}.vlans.{vname}.evpn'

      evpn.evi = evpn.evi or node.vlans[vname].id
      data.must_be_int(
        evpn,'evi',epath,
        module='evpn',
        min_value=1,max_value=65535)
      if not 'rd' in evpn:
        if not rid:
          _routing.router_id(node,'bgp',topology.pools)
          rid = node.bgp.router_id
        evpn.rd = f'{rid}:{node.vlans[vname].id}'
      for rt in ('import','export'):
        if not rt in evpn:
          evpn[rt] = [ f"{node.bgp['as']}:{node.vlans[vname].id}" ]
