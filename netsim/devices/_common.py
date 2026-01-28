#
# Common quirks that can be used by more than one device
#
from box import Box

from ..utils import log
from . import report_quirk


def check_indirect_static_routes(node: Box) -> None:
  for sr_entry in node.get('routing.static',[]):
    if 'discard' in sr_entry.nexthop:
      continue
    if 'intf' not in sr_entry.nexthop:
      report_quirk(
        f'static routes with indirect next hops cannot be used (node {node.name})',
        node=node,
        quirk='indirect_nexthop',
        more_data=f'Static route data: {sr_entry}')

def requires_plugin(node: Box, plugin: str, topology: Box) -> None:
  if plugin not in topology.get('plugin',[]):
    log.error(
      f'Device {node.device} (node {node.name}) requires "{plugin}" plugin to work properly',
      more_hints=f'Add "{plugin}" to the topology "plugin" list',
      category=log.MissingDependency,
      module=node.device)
