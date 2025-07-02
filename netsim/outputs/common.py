#
# Common inventory-related routines (used by Ansible and Devices)
#

import typing
from box import Box
from ..augment import devices
from ..data import get_empty_box,get_box

topo_to_host = { 'mgmt.ipv4': 'ansible_host', 'hostname': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def provider_inventory_settings(node: Box, defaults: Box) -> None:
  p_data = defaults.providers[defaults.provider]
  if not p_data:
    return        # pragma: no cover -- won't create an extra test case just to cover the "do nothing" scenario

  if 'inventory' in p_data:
    for k,v in p_data['inventory'].items():
      node[k] = v

  if 'inventory_port_map' in p_data and 'forwarded' in p_data:
    for k,v in p_data['inventory_port_map'].items():
      if k in p_data['forwarded']:
        node[v] = p_data['forwarded'][k] + node['id']

def add_group_vars(
      host: Box,
      node: Box,
      defaults: Box) -> None:

  group_vars = devices.get_device_attribute(node,'group_vars',defaults)
  if isinstance(group_vars,dict):
    for (k,v) in group_vars.items():
      host[k] = v

def adjust_inventory_host(
      node: Box,
      defaults: Box,
      translate: typing.Optional[dict] = None,
      ignore: typing.Optional[list] = None,
      group_vars: typing.Optional[bool] = False) -> Box:
  host = get_empty_box()

  translate = translate or topo_to_host
  if ignore is None:
    ignore = topo_to_host_skip

  if group_vars:
    add_group_vars(host,node,defaults)

  for (node_key,inv_key) in translate.items():
    if "." in node_key:
      value = node[node_key]
    else:
      value = node.get(node_key,None)
    if value:
      host[inv_key] = value

  for (k,v) in node.items():
    if not k in ignore:
      host[k] = v

  provider_inventory_settings(host,defaults)
  return host

def create_adjusted_topology(topology: Box, ignore: typing.Optional[list] = ['name']) -> Box:
  topo_copy = get_box(topology.to_dict())
  for node in list(topo_copy.nodes.keys()):
    topo_copy.nodes[node] = adjust_inventory_host(
                              node=topo_copy.nodes[node],
                              defaults=topology.defaults,
                              ignore=ignore,
                              group_vars=True)
  return topo_copy
