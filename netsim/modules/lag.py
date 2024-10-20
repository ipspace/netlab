import typing
import netaddr

from box import Box, BoxList
from . import _Module, _dataplane
from .. import data
from ..utils import log
from ..augment import devices, links

ID_SET = 'lag_id'

"""
populate_lag_id_set -- Collect any user defined lag.ifindex values globally and initialize ID generator
"""
def populate_lag_id_set(topology: Box) -> None:
  _dataplane.create_id_set(ID_SET)
  LAG_IDS = { l.lag.ifindex for l in topology.links if 'lag' in l and 'ifindex' in l.lag }
  _dataplane.extend_id_set(ID_SET,LAG_IDS)
  _dataplane.set_id_counter(ID_SET,topology.defaults.lag.start_lag_id,100)

"""
check_lag_feature -- Verify that all nodes involved in a LAG link support the feature
"""
def check_lag_feature(memberlink: Box,topology: Box) -> bool:

  # Check that lag member links have exactly 2 nodes
  if len(memberlink.interfaces)!=2:
    log.error(
      f'Link {memberlink._linkname} in LAG {memberlink.lag.ifindex} must have exactly 2 nodes',
      category=log.IncorrectAttr,
      module='lag')
    return False

  ok = True
  for i in memberlink.interfaces:
    n = topology.nodes[i.node]
    features = devices.get_device_features(n,topology.defaults)
    if 'lag' not in features:
      log.error(
          f'Node {n.name} does not support LAG configured on link {memberlink._linkname}',
          category=log.IncorrectAttr,
          module='lag',
          hint='lag')
      ok = False
    ATT = 'lag.lacp_mode'
    lacp_mode = i.get(ATT) or memberlink.get(ATT) or n.get(ATT) or topology.defaults.get(ATT)
    if lacp_mode=='passive' and not features.lag.get('passive',False):
      log.error(
          f'Node {n.name} does not support passive LACP configured on link {memberlink._linkname}',
          category=log.IncorrectAttr,
          module='lag',
          hint='lag')
      ok = False
  return ok

"""
create_lag_member_links -- iterate over topology.links and expand any that have lag.members defined
"""
def create_lag_member_links(topology: Box) -> None:
  for l in list(topology.links):
      if 'lag' in l:
        if not 'members' in l.lag:
          log.error(
            f'must define "lag.members" on link {l._linkname}',
            category=log.IncorrectAttr,
            module='lag')
        l.type = 'lag'

        if 'ifindex' not in l.lag:                   # Use user provided lag.ifindex, if any
          l.lag.ifindex = _dataplane.get_next_id(ID_SET)

        copy_link_data = data.get_box(l)             # We'll copy all link data into member links
        copy_link_data.type = "p2p"                  # Mark as p2p
        copy_link_data.prefix = False                # Don't allow IP assignment for these links
        for k in ['vlan','lag.members']:             # Remove lag.members and any VLAN parameters 
          copy_link_data.pop(k,None)

        lag_members = l.lag.members
        l.lag.pop("members",None)                    # Remove explicit list of members
        for idx,member in enumerate(lag_members):
          member = links.adjust_link_object(member,f'lag{l.lag.ifindex}[{idx+1}]',topology.nodes)

          # After normalizing, check that all nodes involved support LAGs
          if check_lag_feature(member,topology):
            member = copy_link_data + member         # Copy group data into member link
            member.linkindex = len(topology.links)+1
            member.parentindex = l.linkindex         # Keep track of parent
            if log.debug_active('lag'):
              print(f'LAG create_lag_member_links -> adding link {member}')
            topology.links.append(member)

            if not l.interfaces:                     # Copy interfaces from first member link
              l.interfaces = member.interfaces + []  # Deep copy, assumes all links have same 2 nodes

class LAG(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    if log.debug_active('lag'):
      print(f'LAG module_pre_transform')
    populate_lag_id_set(topology)

    # Expand lag.members into additional p2p links
    create_lag_member_links(topology)
