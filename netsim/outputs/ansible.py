#
# Create Ansible inventory
#
import typing

import yaml
import os
from box import Box

from .. import common
from . import _TopologyOutput

forwarded_port_name = { 'ssh': 'ansible_port', }

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

topo_to_host = { 'mgmt.ipv4': 'ansible_host', 'hostname': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node: Box, defaults: Box) -> Box:
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

  provider_inventory_settings(host,defaults)
  return host

def create(nodes: typing.List[Box], groups: Box, defaults: Box, addressing: typing.Optional[Box] = None) -> Box:
  inventory = Box({},default_box=True,box_dots=True)

  inventory.all.vars.netlab_provider = defaults.provider

  if addressing:
    inventory.all.vars.pools = addressing
    for name,pool in inventory.all.vars.pools.items():
      for k in list(pool.keys()):
        if ('_pfx' in k) or ('_eui' in k):
          del pool[k]

  for node in nodes:
    group = node.get('device','all')
    if not group in inventory:
      inventory[group] = { 'hosts': {} }
    inventory[group]['hosts'][node['name']] = ansible_inventory_host(node,defaults)

  if 'devices' in defaults:
    for group in inventory.keys():
      if group in defaults['devices']:
        group_vars = defaults['devices'][group].get('group_vars')
        if group_vars:
          inventory[group]['vars'] = group_vars

  for gname,gdata in groups.items():
    if not gname in inventory:
      inventory[gname] = { 'hosts': {} }

    if 'vars' in gdata:
      inventory[gname].vars = inventory[gname].get('vars',{}) + gdata.vars

    if 'members' in gdata:
      for node in gdata.members:
        if not node in inventory[gname].hosts:
          inventory[gname].hosts[node] = {}

  return inventory

def dump(data: Box) -> None:
  print("Ansible inventory data")
  print("===============================")
  inventory = create(data.nodes,data.get('groups',{}),data.defaults)
  print(inventory.to_yaml())

def write_yaml(data: Box, fname: str, header: str) -> None:
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    if callable(getattr(data,"to_yaml",None)):
      output.write(data.to_yaml())
    else:                            # pragma: no cover -- this should never happen as we're using Box, but just in case...
      output.write(yaml.dump(data))
    output.close()

min_inventory_data = [ 'id','ansible_host','ansible_port' ]

def ansible_inventory(data: Box, fname: typing.Optional[str] = 'hosts.yml', hostvars: typing.Optional[str] = 'dirs') -> None:
  inventory = create(data['nodes'],data.get('groups',{}),data.get('defaults',{}),data.get('addressing',{}))

#  import ipdb; ipdb.set_trace()
  header = "# Ansible inventory created from %s\n#\n---\n" % data.get('input','<unknown>')

  if not fname:
    fname = 'hosts.yml'
  if not hostvars:
    hostvars = "dirs"

  if hostvars == "min":
    write_yaml(inventory,fname,header)
    print("Created single-file Ansible inventory %s" % fname)
  else:
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
    output.write(common.template('ansible.cfg.j2',{ 'inventory': inventory_file or 'hosts.yml' },'templates'))
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

    ansible_inventory(topology,hostfile,output_format)
    ansible_config(configfile,hostfile)
