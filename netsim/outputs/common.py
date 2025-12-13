#
# Common inventory-related routines (used by Ansible and Devices)
#

import typing

from box import Box

from ..augment import devices
from ..data import get_box, get_empty_box


def provider_inventory_settings(node: Box, defaults: Box) -> None:
  n_provider = devices.get_provider(node,defaults)
  p_data = defaults.providers[n_provider]
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
      defaults: Box) -> typing.Optional[Box]:

  group_vars = devices.get_device_attribute(node,'group_vars',defaults)
  if isinstance(group_vars,dict):
    for (k,v) in group_vars.items():
      host[k] = v

  return group_vars

def add_device_provider_group_vars(host: Box, node: Box, defaults: Box) -> None:
  p_data = devices.get_provider_data(node,defaults)
  if not 'group_vars' in p_data:
    return

  for k,v in p_data.group_vars.items():
    if k not in host:
      host[k] = v

topo_to_host = { 'hostname': 'ansible_host', 'mgmt.ipv4': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def adjust_inventory_host(
      node: Box,
      defaults: Box,
      translate: typing.Optional[dict] = None,
      ignore: typing.Optional[list] = None,
      group_vars: typing.Optional[bool] = False) -> Box:
  host = get_empty_box()

  if group_vars:                                  # Add group variables before doing netlab-to-ansible
    g_vars = add_group_vars(host,node,defaults)   # ... attribute conversion because we need 'ansible_connection'
  else:
    # The caller does not want to have group vars copied into node data, but we still have to do that
    # for provider group_vars on nodes with non-default provider, as they might have (for example)
    # different ansible_connection
    #
    g_vars = devices.get_device_attribute(node,'group_vars',defaults)
    n_provider = devices.get_provider(node,defaults)
    if n_provider != defaults.provider:
      add_device_provider_group_vars(host,node,defaults)

  translate = translate or topo_to_host
  if ignore is None:
    ignore = topo_to_host_skip

  # For Docker nodes, do not use mgmt.X attributes (to set ansible_host)
  # Everywhere else, 'mgmt.ipv4' will overwrite 'hostname' (set by clab)
  # resulting in an IPv4 address, not a hostname, for nodes using SSH/HTTPx
  # connections, making ansible-pysshlib happy (see #2911)
  ansible_connection = host.get('ansible_connection','')
  if not ansible_connection and isinstance(g_vars,dict):
    ansible_connection = g_vars.get('ansible_connection','')
  if ansible_connection == 'docker':
    translate = { k:v for k,v in translate.items() if 'mgmt.' not in k }

  for (node_key,inv_key) in translate.items():
    value = node.get(node_key,None)
    if value is not None:
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
