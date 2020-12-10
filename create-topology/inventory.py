#
# Create Ansible inventory
#

import yaml
import os
import sys

topo_to_host = { 'mgmt_ip': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node):
  host = {}
  for (node_key,inv_key) in topo_to_host.items():
    if node.get(node_key):
      host[inv_key] = node[node_key]

  for (k,v) in node.items():
    if not k in topo_to_host_skip:
      host[k] = v

  return host

def create(nodes,defaults):
  inventory = {}

  for node in nodes:
    group = node.get('device','all')
    if not group in inventory:
      inventory[group] = { 'hosts': {} }
    inventory[group]['hosts'][node['name']] = ansible_inventory_host(node)

  if 'devices' in defaults:
    for group in inventory.keys():
      if group in defaults['devices']:
        group_vars = defaults['devices'][group].get('group_vars')
        if group_vars:
          inventory[group]['vars'] = group_vars

  return inventory

def dump(data):
  print(yaml.dump(create(data['nodes'],data.get('defaults',{}))))

def write_yaml(data,fname,header):
  dirname = os.path.dirname(fname)
  if dirname and not os.path.exists(dirname):
    os.makedirs(dirname)

  with open(fname,"w") as output:
    output.write(header)
    output.write(yaml.dump(data))
    output.close()

min_inventory_data = [ 'id','ansible_host' ]

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