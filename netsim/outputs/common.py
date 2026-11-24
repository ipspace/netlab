#
# Common inventory-related routines (used by Ansible and Devices)
#

import typing

from box import Box

from ..augment import devices
from ..data import append_to_list, get_box, get_empty_box, global_vars

"""
Copy provider-specific inventory settings into node data. Used primarily to set up port forwarding
"""
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

"""
Add group variables (generic device variables and/or device/provider variables) to a copy of node data
"""
def add_group_vars(
      host: Box,
      node: Box,
      defaults: Box,
      provider_only: bool = False) -> typing.Optional[Box]:

  if provider_only:
    group_vars = devices.get_provider_data(node,defaults).get('group_vars',{})
  else:
    group_vars = devices.get_device_attribute(node,'group_vars',defaults)

  if isinstance(group_vars,dict):
    for k,v in group_vars.items():
      if k not in host:
        host[k] = v

  return group_vars

topo_to_host = { 'hostname': 'ansible_host', 'mgmt.ipv4': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def adjust_inventory_host(
      node: Box,
      defaults: Box,
      translate: typing.Optional[dict] = None,
      ignore: typing.Optional[list] = None,
      group_vars: typing.Optional[bool] = False,
      template_vars: typing.Optional[bool] = False) -> Box:
  host = get_empty_box()

  n_provider = devices.get_provider(node,defaults)
  if group_vars:                                  # Add group variables before doing netlab-to-ansible
    g_vars = add_group_vars(host,node,defaults)   # ... attribute conversion because we need 'ansible_connection'
  else:
    # The caller does not want to have group vars copied into node data, but we still have to do that
    # for provider group_vars on nodes with non-default provider, as they might have (for example)
    # different ansible_connection
    #
    g_vars = devices.get_device_attribute(node,'group_vars',defaults)
    if n_provider != defaults.provider:
      add_group_vars(host,node,defaults,provider_only=True)

  translate = translate or topo_to_host
  if ignore is None:
    ignore = topo_to_host_skip

  if template_vars:
    node.inventory_hostname = node.name
    node.netlab_device_type = host.get('netlab_device_type',host.get('ansible_network_os','none'))
    node.node_provider = n_provider
    node.netlab_interfaces = ([ node.get('loopback')] if 'loopback' in node else []) + \
                             node.get('interfaces',[])

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

def create_adjusted_topology(
      topology: Box,
      ignore: typing.Optional[list] = ['name'],
      template_vars: bool = False) -> Box:
  topo_copy = get_box(topology.to_dict())
  for node in list(topo_copy.nodes.keys()):
    topo_copy.nodes[node] = adjust_inventory_host(
                              node=topo_copy.nodes[node],
                              defaults=topology.defaults,
                              ignore=ignore,
                              group_vars=True,
                              template_vars=template_vars)
  return topo_copy

"""
Create a 'hosts' dictionary listing usable IPv4 and IPv6 addresses of all lab devices.
"""
def get_host_addresses(topology: Box) -> Box:
  hosts = global_vars.get('hosts')                          # Try to use a cached version
  if hosts:
    return hosts

  from ..utils import routing as _rp_utils
  for name in sorted(topology.nodes):
    node = topology.nodes[name]
    intf_list = node.interfaces
    if 'loopback' in node:                                  # Create a list of all usable interfaces
      intf_list = [ node.loopback ] + node.interfaces       # ... starting with loopback
      for af in ['ipv4','ipv6']:
        # If the loopback interface has the desired address, extract IP address from the CIDR prefix
        #
        if af in node.loopback and isinstance(node.loopback[af],str):
          lb = _rp_utils.get_intf_address(node.loopback[af])
          append_to_list(hosts[name],'loopback',lb)

    for intf in intf_list:                                  # Now iterate over interfaces
      h_name = f'{name}-{intf.vrf}' if 'vrf' in intf else name
      for af in ('ipv4','ipv6'):                            # ... and collect IPv4 and IPv6 addresses
        if not isinstance(intf.get(af,False),str):          # Is the IP address a string (= usable IP address)?
          continue

        addr = _rp_utils.get_intf_address(intf[af])         # Extract IP address from the CIDR prefix
        append_to_list(hosts[h_name],af,addr)               # ... and append it to the list of usable IP addresses

  global_vars.set('hosts',hosts)                            # Cache the hosts dictionary
  return hosts
