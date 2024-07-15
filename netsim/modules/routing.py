#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing, re
import netaddr
from box import Box

from . import _Module,_routing,_dataplane,get_effective_module_attribute
from ..utils import log
from .. import data
from ..data import global_vars
from ..data.types import must_be_list
from ..augment import devices,groups,links,addressing

set_kw: typing.Optional[Box] = None

def normalize_policy_entry(p_entry: Box, p_idx: int) -> Box:
  global set_kw

  if set_kw is None:                                        # Premature optimization: cache the SET keywords
    topology = global_vars.get_topology()
    if topology is None:
      return p_entry
    set_kw = topology.defaults.routing.attributes.route_map.set

  for k in set_kw:
    if k not in p_entry:
      continue

    p_entry.set[k] = p_entry[k]
    p_entry.pop(k,None)

  if 'action' not in p_entry:
    p_entry.action = 'permit'

  if 'sequence' not in p_entry:
    p_entry.sequence = (p_idx + 1) * 10

  return p_entry

def transform_policy(pdata: typing.Optional[Box]) -> None:
  if pdata is None:
    return

  for pname in list(pdata.keys()):
    if isinstance(pdata[pname],Box):
      pdata[pname] = [ pdata[pname] ]

    if not isinstance(pdata[pname],list):
      continue

    for p_idx,p_entry in enumerate(pdata[pname]):
      if not isinstance(pdata[pname][p_idx],dict):
        continue
      pdata[pname][p_idx] = normalize_policy_entry(pdata[pname][p_idx],p_idx)

class Routing(_Module):

  def module_pre_default(self, topology: Box) -> None:
    transform_policy(topology.get('routing.policy',None))

  def node_pre_default(self, node: Box, topology: Box) -> None:
    node_pdata = node.get('routing.policy',None)
    if node_pdata is None:
      return

    topo_pdata = topology.get('routing.policy',{})
    for p_name in list(node_pdata.keys()):
      if node_pdata[p_name] is not None:
        continue
      if not p_name in topo_pdata:
        log.error(
          f'Global policy {p_name} referenced in node {node.name} policy table does not exist',
          category=log.MissingValue,
          module='routing')
        continue

      node_pdata[p_name] = topo_pdata[p_name]

    transform_policy(node_pdata)
