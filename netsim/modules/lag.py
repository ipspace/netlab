import typing
import netaddr

from box import Box, BoxList
from . import _Module, _dataplane
from .. import data
from ..data import types as _types
from ..utils import log
from ..augment import devices, links

ID_SET = 'lag_id'

"""
populate_lag_id_set -- Collect any user defined lag.ifindex values globally and initialize ID generator
"""
def populate_lag_id_set(topology: Box) -> None:
  _dataplane.create_id_set(ID_SET)
  # Note that 0 is a valid lag.ifindex value
  LAG_IDS = { l.lag.ifindex for l in topology.links if 'lag' in l and 'ifindex' in l.lag }
  _dataplane.extend_id_set(ID_SET,LAG_IDS)
  _dataplane.set_id_counter(ID_SET,topology.defaults.lag.start_lag_id,100)

"""
create_lag_member_links -- iterate over topology.links and expand any that have lag.members defined
"""
def create_lag_member_links(topology: Box) -> None:
  for l in list(topology.links):
      if 'lag' not in l:
        continue
      elif not 'members' in l.lag:
        log.error(f'must define "lag.members" on LAG link {l._linkname}',
          category=log.IncorrectAttr,
          module='lag')
      elif not _types.must_be_list(parent=l.lag,key='members',path=l._linkname,module='lag'):
        return

      l.type = 'lag'
      if 'ifindex' not in l.lag:                     # Use user provided lag.ifindex, if any
        l.lag.ifindex = _dataplane.get_next_id(ID_SET)
      l2_ifdata = { 'type': "p2p", 'prefix': False } # Construct an L2 member link
      for a in list(topology.defaults.lag.attributes.lag_l2_ifattr):
        if a in l:
          l2_ifdata[a] = l[a]

      lag_members = l.lag.members
      l.lag.pop("members",None)                      # Remove explicit list of members
      for idx,member in enumerate(lag_members):
        member = links.adjust_link_object(member,f'{l._linkname}.lag[{idx+1}]',topology.nodes)

        if len(member.interfaces)!=2:                # Check that there are exactly 2 nodes involved
          log.error(f'Link {member._linkname} in LAG {l.lag.ifindex} must have exactly 2 nodes',
          category=log.IncorrectAttr,
          module='lag')
        else:                                        # Check that they all support LAG
          for i in member.interfaces:
            _n = topology.nodes[i.node]
            features = devices.get_device_features(_n,topology.defaults)
            if 'lag' not in features:
              log.error(f'Node {_n.name} ({_n.device}) does not support lag module, cannot be part of LAG {member._linkname}',
                category=log.IncorrectAttr,
                module='lag')
              return
            if 'lag' not in _n.get('module',[]):
              log.error(f'lag module not enabled for node {_n.name}, cannot be part of LAG {member._linkname}',
                category=log.IncorrectAttr,
                module='lag')
              return

        member = l2_ifdata + member                  # Copy L2 data into member link
        member.linkindex = len(topology.links)+1
        member.parentindex = l.linkindex             # Keep track of parent
        if log.debug_active('lag'):
          print(f'LAG create_lag_member_links -> adding link {member}')
        topology.links.append(member)
        if not l.interfaces:                         # Copy interfaces from first member link
          l.interfaces = member.interfaces + []      # Deep copy, assumes all links have same 2 nodes
        else:
          base = { n.node for n in l.interfaces }    # List the (2) nodes from the first link
          others = { n.node for n in member.interfaces if n.node not in base }
          if others:
            log.error(f'All LAG link members must connect the same pair of nodes({base}), found {others}',
              category=log.IncorrectAttr,
              module='lag')

class LAG(_Module):

  def module_pre_transform(self, topology: Box) -> None:
    if log.debug_active('lag'):
      print(f'LAG module_pre_transform')
    populate_lag_id_set(topology)

    # Expand lag.members into additional p2p links
    create_lag_member_links(topology)

  """
  After attribute propagation and consolidation, verify that requested features are supported

  Only gets called for nodes with 'lag' module enabled
  """
  def node_post_transform(self, node: Box, topology: Box) -> None:
    features = devices.get_device_features(node,topology.defaults)
    for i in node.interfaces:
      if 'lag' not in i:
        continue

      lacp_mode = i.get('lag.lacp_mode')  # Inheritance copying is done elsewhere
      if lacp_mode=='passive' and not features.lag.get('passive',False):
        log.error(f'Node {node.name} does not support passive LACP configured on interface {i.ifname}',
          category=log.IncorrectAttr,
          module='lag',
          hint='lag')
