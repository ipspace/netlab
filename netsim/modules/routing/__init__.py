#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing

from box import Box, BoxList

from ...augment import devices
from ...data import global_vars
from ...utils import log
from .. import _Module
from . import aspath, clist, policy, prefix, static
from .normalize import (
  check_routing_object,
  import_routing_object,
  normalize_routing_entry,
  normalize_routing_objects,
  process_routing_data,
)

"""
Dispatch table for global-to-node object import
"""
import_dispatch: typing.Dict[str,dict] = {
  'policy': {
    'import' : policy.import_routing_policy,
    'check'  : policy.check_routing_policy,
    'related': policy.import_policy_filters },
  'prefix': {
    'import' : import_routing_object,
    'check'  : check_routing_object },
  'aspath': {
    'import' : import_routing_object,
    'check'  : check_routing_object },
  'community': {
    'import' : clist.import_community_list,
    'check'  : check_routing_object },
  'static': {
    'start'  : static.include_global_static_routes
  }
}

"""
Dispatch table for data normalization
"""
normalize_dispatch: typing.Dict[str,dict] = {
  'policy':
    { 'namespace': 'routing.policy',
      'object'   : 'policy',
      'callback' : policy.normalize_policy_entry },
  'prefix':
    { 'namespace': 'routing.prefix',
      'object'   : 'prefix filter',
      'callback' : normalize_routing_entry },
  'aspath':
    { 'namespace': 'routing.aspath',
      'object'   : 'AS path filter',
      'callback' : aspath.normalize_aspath_entry },
  'community':
    { 'namespace': 'routing.community',
      'object'   : 'BGP community filter',
      'callback' : aspath.normalize_aspath_entry },
}

"""
normalize_routing_data: execute the normalization functions for all routing objects
"""
def normalize_routing_data(r_object: Box, topo_object: bool = False, o_name: str = 'topology') -> None:
  global normalize_dispatch

  try:
    for dp in normalize_dispatch.values():
      if 'transform' in dp:
        if dp['namespace'] in r_object:
          xform = r_object[dp['namespace']]
          xform = dp['transform'](xform,o_type=dp['object'],topo_object=topo_object,o_name=o_name)
          if xform is not None:
            r_object[dp['namespace']] = xform
      elif 'callback' in dp:
        normalize_routing_objects(
          o_dict=r_object.get(dp['namespace'],None),
          o_type=dp['object'],
          normalize_callback=dp['callback'],
          topo_object=topo_object)
  except Exception as ex:
    log.warning(
      text=f"Cannot normalize {o_name} routing objects",
      more_data=str(ex),
      more_hints="Check further error messages for more details",
      module='routing')

"""
Dispatch table for post-transform processing. Currently used only to
expand the prefixes/pools in prefix list.
"""
transform_dispatch: typing.Dict[str,dict] = {
  'policy': {
    'import': policy.adjust_routing_policy
  },
  'prefix': {
    'import': prefix.expand_prefix_list
  },
  'aspath': {
    'import': aspath.number_aspath_acl
  },
  'community': {
    'import': clist.expand_community_list
  },
  'static': {
    'start'  : static.process_static_route_includes,
    'import' : static.import_static_routes,
    'check'  : static.check_static_routes,
    'cleanup': static.cleanup_static_routes
  }
}

class Routing(_Module):

  """
  Normalize routing object shortcuts into data structures that will pass validation
  This step has to be implemented as a static "normalize" hook to be executed before
  group data validation.
  """
  def module_normalize(self, topology: Box) -> None:
    normalize_routing_data(topology,topo_object=True,o_name='topology')

    for gname,gdata in topology.get('groups',{}).items():
      if gname.startswith('_'):
        continue
      normalize_routing_data(gdata,o_name=f'groups.{gname}')

    for node,ndata in topology.nodes.items():
      normalize_routing_data(ndata,o_name=f'nodes.{node}')

  """
  The routing module defines two standard prefixes in the topology defaults. These
  prefixes have to be merged with topology prefixes before any serious transformation
  work starts.
  """
  def module_pre_default(self, topology: Box) -> None:
    topology.prefix = topology.defaults.prefix + topology.prefix

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    global import_dispatch

    for o_name in import_dispatch.keys():
      process_routing_data(node,o_name,topology,import_dispatch,always_check=True)

  def node_post_transform(self, node: Box, topology: Box) -> None:
    global transform_dispatch

    for o_name in transform_dispatch.keys():
      process_routing_data(node,o_name,topology,transform_dispatch)
