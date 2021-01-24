#
# Create Ansible inventory
#

import yaml
import os
import sys
import common

forwarded_port_name = { 'ssh': 'ansible_port', }

def provider_inventory_settings(node,defaults):
  p_data = common.get_value(defaults,[ 'providers',defaults['provider']])
  if not p_data:
    return

  if 'inventory' in p_data:
    for k,v in p_data['inventory'].items():
      node[k] = v

  if 'inventory_port_map' in p_data and 'forwarded' in p_data:
    for k,v in p_data['inventory_port_map'].items():
      if k in p_data['forwarded']:
        node[v] = p_data['forwarded'][k] + node['id']

topo_to_host = { 'mgmt.ipv4': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node,defaults):
  host = {}
  for (node_key,inv_key) in topo_to_host.items():
    value = common.get_value(node,node_key.split('.'))
    if value:
      host[inv_key] = value

  for (k,v) in node.items():
    if not k in topo_to_host_skip:
      host[k] = v

  provider_inventory_settings(host,defaults)
  return host

def create(nodes,defaults):
  inventory = {}

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

  return inventory

def dump(data):
  print("Ansible inventory data")
  print("===============================")
  print(yaml.dump(create(data['nodes'],data.get('defaults',{}))))

def write_yaml(data,fname,header):
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    output.write(yaml.dump(data))
    output.close()

min_inventory_data = [ 'id','ansible_host','ansible_port' ]

def write(data,fname,hostvars):
  inventory = create(data['nodes'],data.get('defaults',{}))
  header = "# Ansible inventory created from %s\n#\n---\n" % data.get('input','<unknown>')

  if not hostvars:
    write_yaml(inventory,fname,header)
    print("Created single-file Ansible inventory %s" % fname)
  else:
    for g in inventory.keys():
      gvars = inventory[g].pop('vars',None)
      if gvars:
        write_yaml(gvars,'group_vars/%s/topology.yml' % g,header)
        print("Created group_vars for %s" % g)

      if 'hosts' in inventory[g]:
        hosts = inventory[g]['hosts']
        for h in hosts.keys():
          min_host = {}
          vars_host = {}
          for item in hosts[h].keys():
            if item in min_inventory_data:
              min_host[item] = hosts[h][item]
            else:
              vars_host[item] = hosts[h][item]

          write_yaml(vars_host,'host_vars/%s/topology.yml' % h,header)
          print("Created host_vars for %s" % h)
          hosts[h] = min_host

    write_yaml(inventory,fname,header)
    print("Created minimized Ansible inventory %s" % fname)

def config(config_file,inventory_file,path):
  with open(config_file,"w") as output:
    output.write(common.template('ansible.cfg.j2',{ 'inventory': inventory_file },path + '/templates'))
    output.close()
    print("Created Ansible configuration file: %s" % config_file)
