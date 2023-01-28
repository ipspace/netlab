#
# Create Ansible inventory
#
import typing

import yaml
import os
from box import Box

from .. import common
from . import _TopologyOutput
from ..augment import nodes
from ..augment import devices

forwarded_port_name = { 'ssh': 'ansible_port', }

def copy_provider_inventory(host: Box, p_data: Box) -> None:
  if 'inventory' in p_data:
    for k,v in p_data.inventory.items():
      host[k] = v

  if 'inventory_port_map' in p_data and 'forwarded' in p_data:
    for k,v in p_data.inventory_port_map.items():
      if k in p_data.forwarded:
        host[v] = p_data.forwarded[k] + host.id

def copy_device_provider_group_vars(host: Box, node: Box, topology: Box) -> None:
  p_data = devices.get_provider_data(node,topology.defaults)
  if not 'group_vars' in p_data:
    return

  for k,v in p_data.group_vars.items():
    if not k in host:
      host[k] = v

def provider_inventory_settings(host: Box, node: Box, topology: Box) -> None:
  defaults = topology.defaults
  node_provider = devices.get_provider(node,topology)
  p_data = defaults.providers[node_provider]
  if p_data:
    copy_provider_inventory(host,p_data)

  if 'provider' in node:                                              # Is the node using a secondary provider?
    copy_device_provider_group_vars(host,node,topology)

topo_to_host = { 'mgmt.ipv4': 'ansible_host', 'hostname': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node: Box, topology: Box) -> Box:
  defaults = topology.defaults
  host = Box({})
  for (node_key,inv_key) in topo_to_host.items():
    if "." in node_key:
      value = node[node_key]
    else:
      value = node.get(node_key,None)
    if value:
      host[inv_key] = value

  for (k,v) in node.items():
    if not k in topo_to_host_skip:
      host[k] = v

  provider_inventory_settings(host,node,topology)
  return host

def create(topology: Box) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  inventory.all.vars.netlab_provider = topology.defaults.provider
  inventory.all.vars.netlab_name = topology.name

  inventory.modules.hosts = {}
  inventory.custom_configs.hosts = {}

  defaults = topology.defaults

  if 'module' in topology:
    inventory.modules.vars.netlab_module = topology.module

  if 'addressing' in topology:
    inventory.all.vars.pools = topology.addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  for name,node in topology.nodes.items():
    group = node.get('device','all')
    inventory[group].hosts[name] = ansible_inventory_host(node,topology)

    if 'module' in node:
      inventory.modules.hosts[name] = {}

    if 'config' in node:
      inventory.custom_configs.hosts[name] = {}

  if 'devices' in defaults:
    for group in inventory.keys():
      if group in defaults.devices:
        devdata = defaults.devices[group]
        group_vars = devdata.group_vars + devdata[defaults.provider].group_vars
        if group_vars:
          inventory[group]['vars'] = group_vars

  if not 'groups' in topology:
    return inventory

  for gname,gdata in topology.groups.items():
    if not gname in inventory:
      inventory[gname] = { 'hosts': {} }

    if 'vars' in gdata:
      inventory[gname].vars = inventory[gname].get('vars',{}) + gdata.vars

    if 'members' in gdata:
      for m in gdata.members:
        if m in topology.nodes:
          if not m in inventory[gname].hosts:
            inventory[gname].hosts[m] = {}
        elif m in topology.groups:
          inventory[gname].children[m] = {}

  return inventory

# Note to self: the dump function is used by the testing scripts. Do not remove
#
def dump(data: Box) -> None:
  print("Ansible inventory data")
  print("===============================")
  inventory = create(data)
  print(common.get_yaml_string(inventory))

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    output.write(common.get_yaml_string(data))
    output.close()

min_inventory_data = [ 'id','ansible_host','ansible_port','ansible_connection','ansible_user','ansible_ssh_pass' ]

def ansible_inventory(topology: Box, fname: typing.Optional[str] = 'hosts.yml', hostvars: typing.Optional[str] = 'dirs') -> None:
  inventory = create(topology)

#  import ipdb; ipdb.set_trace()
  header = "# Ansible inventory created from %s\n#\n---\n" % topology.get('input','<unknown>')

  if not fname:
    fname = 'hosts.yml'
  if not hostvars:
    hostvars = "dirs"

  if hostvars == "min":
    write_yaml(inventory,fname,header)
    print("Created single-file Ansible inventory %s" % fname)
    return

  for g in inventory.keys():
    gvars = inventory[g].pop('vars',None)
    if gvars:
      write_yaml(gvars,'group_vars/%s/topology.yml' % g,header)
      if not common.QUIET:
        print("Created group_vars for %s" % g)

    if 'hosts' in inventory[g]:
      hosts = inventory[g]['hosts']
      for h in hosts.keys():
        if not hosts[h]:
          continue
        min_host = Box({})
        vars_host = Box({})
        for item in hosts[h].keys():
          if item in min_inventory_data:
            min_host[item] = hosts[h][item]
          else:
            vars_host[item] = hosts[h][item]

        write_yaml(vars_host,'host_vars/%s/topology.yml' % h,header)
        if not common.QUIET:
          print("Created host_vars for %s" % h)
        hosts[h] = min_host

  write_yaml(inventory,fname,header)
  print("Created minimized Ansible inventory %s" % fname)

def ansible_config(config_file: typing.Union[str,None] = 'ansible.cfg', inventory_file: typing.Union[str,None] = 'hosts.yml') -> None:
  if not config_file:
    config_file = 'ansible.cfg'
  if not inventory_file:
    inventory_file = 'hosts.yml'

  with open(config_file,"w") as output:
    output.write(common.template('ansible.cfg.j2',{ 'inventory': inventory_file or 'hosts.yml' },'templates','ansible'))
    output.close()
    if not common.QUIET:
      print("Created Ansible configuration file: %s" % config_file)

class AnsibleInventory(_TopologyOutput):

  def write(self, topology: Box) -> None:
    hostfile = self.settings.hostfile or 'hosts.yml'
    configfile = self.settings.configfile or 'ansible.cfg'
    output_format = None

    if hasattr(self,'filenames'):
      hostfile = self.filenames[0]
      if len(self.filenames) > 1:
        configfile = self.filenames[1]
      if len(self.filenames) > 2:
        common.error('Extra output filename(s) ignored: %s' % str(self.filenames[2:]),common.IncorrectValue,'ansible')

    if self.format:
      output_format = self.format[0]
    
    # Creates a "ghost clean" topology
    # (AKA, remove unmanaged devices)
    ansible_topology = nodes.ghost_buster(topology)

    ansible_inventory(ansible_topology,hostfile,output_format)
    ansible_config(configfile,hostfile)
