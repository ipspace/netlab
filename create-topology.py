#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import argparse
import yaml
import json
import re
import netaddr

from jinja2 import Environment, FileSystemLoader, Undefined, StrictUndefined, make_logging_undefined

LOGGING=False
VERBOSE=False

def parseCLI():
  parser = argparse.ArgumentParser(description='Create topology data from topology description')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file')
  parser.add_argument('--defaults', dest='defaults', action='store', default='topology-defaults.yml',
                  help='Local topology defaults')
  parser.add_argument('-x','--expanded', dest='xpand', action='store', nargs='?', const='topology-expanded.yml',
                  help='Create expanded topology file')
  parser.add_argument('-g','--vagrantfile', dest='vagrant', action='store', nargs='?', const='Vagrantfile',
                  help='Create Vagrantfile')
  parser.add_argument('-i','--inventory', dest='inventory', action='store', nargs='?', const='hosts.yml',
                  help='Create Ansible inventory file')
  parser.add_argument('--hostvars', dest='hostvars', action='store_true',
                  help='Create Ansible hostvars')
  parser.add_argument('--log', dest='logging', action='store_true',
                  help='Enable basic logging')
  parser.add_argument('-q','--quiet', dest='quiet', action='store_true',
                  help='Report only major errors')
  parser.add_argument('-v','--verbose', dest='verbose', action='store_true',
                  help='Enable more verbose logging')
  return parser.parse_args()

def fatal(text):
  print(text,file=sys.stderr)
  sys.exit(1)

def merge_defaults(data,defaults):
  if not data:
    return defaults

  if type(data) is dict and type(defaults) is dict:
    for (k,v) in defaults.items():
      data[k] = merge_defaults(data.get(k),defaults[k])
  return data

def read_yaml(fname):
  try:
    stream = open(fname,'r')
  except:
    if LOGGING or VERBOSE:
      print("Cannot open YAML file %s" % fname)
    return None

  try:
    data = yaml.load(stream,Loader=yaml.SafeLoader)
  except:
    fatal("Cannot read YAML from %s: %s " % (fname,sys.exc_info()[0]))
  stream.close()
  if LOGGING or VERBOSE:
    print("Read YAML data from %s" % fname)
  return data

def read_topology(fname,defaults):
  topology = read_yaml(fname)
  if topology is None:
    fatal('Cannot open topology file: %s' % sys.exc_info()[0])
  topology['input'] = [ fname ]

  if not 'defaults' in topology:
    topology['defaults'] = {}

  local_defaults = read_yaml(defaults)
  if local_defaults:
    topology['input'].append(defaults)
    merge_defaults(topology['defaults'],local_defaults)

  global_def_fname = os.path.dirname(os.path.realpath(__file__))+"/topology-defaults.yml"
  global_defaults = read_yaml(global_def_fname)
  if global_defaults:
    topology['input'].append(os.path.relpath(global_def_fname))
    merge_defaults(topology['defaults'],global_defaults)

  return topology

def template(j2,data):
  path = os.path.dirname(os.path.realpath(__file__))
  ENV = Environment(loader=FileSystemLoader(path),trim_blocks=True,lstrip_blocks=True)
  template = ENV.get_template(j2)
  return template.render(**data)

def augment_nodes(topology,defaults):
  id = 0

  ndict = {}
  for n in topology['nodes']:
    id = id + 1
    n['id'] = id
    if not 'device' in n:
      n['device'] = defaults.get('device')
      if not n['device'] in defaults.get('devices'):
        print("WARNING: Unsupported device type %s" % n['device'])
    if 'mac' in defaults:
      n['mgmt_mac'] = defaults['mac'] % id

    if 'mgmt' in defaults:
      n['mgmt_ip'] = defaults['mgmt'] % id

    if 'loopback' in defaults:
      n['loopback'] = defaults['loopback'] % id

    if not n.get('name'):
      print("ERROR: node does not have a name %s" % str(n))
      return

    ndict[n['name']] = n

  topology['nodes_map'] = ndict
  return ndict

def add_node_interface(node,ifdata,**kwargs):
  node_links = node.get('links')
  if node_links is None:
    node_links = []

  ifindex = len(node_links) + 1

  defaults = kwargs.get('defaults',{})
  ifname_format = None
  if 'devices' in defaults:
    if node['device'] in defaults['devices']:
      ifname_format = defaults['devices'][node['device']].get('interface_name')

  ifdata['ifindex'] = ifindex
  if ifname_format is not None:
    ifdata['ifname'] = ifname_format % ifindex

  node_links.append(ifdata)
  node['links'] = node_links
  return ifdata

def augment_bridge_link(link,pfx_list,ndict,**kwargs):
  pfx = next(pfx_list)
  link['prefix'] = str(pfx)

  interfaces = {}

  for (node,value) in link.items():
    if node in ndict:
      if value is None:
        value = {}
      ip = netaddr.IPNetwork(pfx[ndict[node]['id']])
      ip.prefixlen = pfx.prefixlen
      value['ip'] = str(ip)
      link[node] = value

      interfaces[node] = add_node_interface(ndict[node], \
         { 'ip' : value['ip'], 'bridge': link['bridge'] }, \
         defaults=kwargs.get('defaults'))

    elif not node in ['bridge','prefix']:
      print("Unknown LAN link attribute '%s': %s" % (node,str(link)))

  for node in interfaces.keys():
    interfaces[node]['neighbors'] = {}
    for remote in interfaces.keys():
      if remote != node:
        interfaces[node]['neighbors'][remote] = { \
          'ip': interfaces[remote]['ip'], \
          'ifname': interfaces[remote]['ifname'] }

def augment_p2p_link(link,pfx_list,ndict,**kwargs):
  end_names = ['left','right']

  pfx = next(pfx_list)
  link['prefix'] = str(pfx)
  augment = {}
  nodes = []
  interfaces = []

  for (node,value) in link.items():
    if node in ndict:
      ecount = len(nodes)
      if value is None:
        value = {}
      ip = netaddr.IPNetwork(pfx[ecount+1])
      ip.prefixlen = pfx.prefixlen
      value['ip'] = str(ip)
      link[node] = value
      nodes.append({ 'name': node, 'link': value })
    elif not node in ['prefix']:
      print("Unknown P2P link attribute '%s': %s" % (node,str(link)))

  if len(nodes) > len(end_names):
    print("Too many nodes specified on a P2P link")
    return

  for i in range(0,len(nodes)):
    node = nodes[i]['name']
    interfaces.append(add_node_interface(ndict[node],{ 'ip': link[node]['ip'] },defaults=kwargs.get('defaults')))

  for i in range(0,2):
    interfaces[i]['remote_id'] = ndict[nodes[1-i]['name']]['id']
    interfaces[i]['remote_ifindex'] = interfaces[1-i]['ifindex']
    interfaces[i]['neighbors'] = { nodes[1-i]['name'] : { \
      'ifname' : interfaces[1-i]['ifname'], \
      'ip': interfaces[1-i]['ip'] }}

  for i in range(0,2):
    link[end_names[i]] = { 'node': nodes[i]['name'], 'ip': interfaces[i]['ip'], 'ifname': interfaces[i].get('ifname') }

  return link

def augment_links(link_list,defaults,ndict):
  lan_pfx   = defaults.get('lan','10.0.0.0/16')
  lan_subnet= defaults.get('lan_subnet',24)
  p2p_pfx   = defaults.get('p2p','10.1.0.0/16')
  p2p_subnet= defaults.get('p2p_subnet',30)
  lan_list  = netaddr.IPNetwork(lan_pfx).subnet(lan_subnet)
  p2p_list  = netaddr.IPNetwork(p2p_pfx).subnet(p2p_subnet)

  for link in link_list:
    # multi-access links have bridge names
    if 'bridge' in link:
      link_prefix_list = p2p_list if link.get('type') == 'p2p' else lan_list
      augment_bridge_link(link,link_prefix_list,ndict,defaults=defaults)
    else:
      augment_p2p_link(link,p2p_list,ndict,defaults=defaults)
  return link_list

def augment_nodes_to_dicts(topology):
  node_list = []
  for n in topology['nodes']:
    node_list.append(n if type(n) is dict else { 'name': n})
  topology['nodes'] = node_list
  return node_list

def augment(topology):
  augment_nodes_to_dicts(topology)
  ndict = augment_nodes(topology,topology.get('defaults',{}))
  augment_links(topology['links'],topology.get('defaults',{}),ndict)

topo_to_host = { 'mgmt_ip': 'ansible_host', 'id': 'id' }
topo_to_host_skip = [ 'name','device' ]

def ansible_inventory_host(node,hostvars):
  host = {}
  for (node_key,inv_key) in topo_to_host.items():
    if node.get(node_key):
      host[inv_key] = node[node_key]

  if hostvars:
    return host

  for (k,v) in node.items():
    if not k in topo_to_host_skip:
      host[k] = v

  return host

def create_ansible_inventory(nodes,defaults,hostvars):
  inventory = {}

  for node in nodes:
    group = node.get('device','all')
    if not group in inventory:
      inventory[group] = { 'hosts': {} }
    inventory[group]['hosts'][node['name']] = ansible_inventory_host(node,hostvars)

  if not(hostvars) and 'devices' in defaults:
    for group in inventory.keys():
      if group in defaults['devices']:
        group_vars = defaults['devices'][group].get('group_vars')
        if group_vars:
          inventory[group]['vars'] = group_vars

  return inventory

def dump_topology_data(topology,state):
  print("%s topology data" % state)
  print("===============================")
  print(yaml.dump(topology))

def write_topology_data(topology,fname):
  with open(fname,"w") as output:
    output.write("# Expanded topology created from %s " % topology.get('input','<unknown>'))
    output.write(yaml.dump(topology))
    output.close()
    print("Created expanded topology file: %s" % args.xpand)

def dump_vagrant_data(topology):
  print("\nVagrantfile")
  print("============================")
  print(template('Vagrantfile.j2',topology))

def create_vagrantfile(topology,fname):
  with open(fname,"w") as output:
    output.write(template('Vagrantfile.j2',topology))
    output.close()
    print("Created Vagrantfile: %s" % args.vagrant)

def dump_inventory_data(data,hostvars):
  print(yaml.dump(create_ansible_inventory(data['nodes'],data.get('defaults',{}),hostvars)))

def write_ansible_inventory(data,fname,hostvars):
  with open(fname,"w") as output:
    output.write("# Ansible inventory created from %s " % data.get('input','<unknown>')+"\n")
    output.write("#\n")
    output.write("---\n")
    output.write(yaml.dump(create_ansible_inventory(data['nodes'],data.get('defaults',{}),hostvars)))
    output.close()

def main():
  args = parseCLI()
  LOGGING = args.logging
  VERBOSE = args.verbose
#  if args.verbose:
#    print(args)

  topology = read_topology(args.topology,args.defaults)
  if args.verbose:
    dump_topology_data(topology,'Collected')

  augment(topology)
  if args.vagrant:
    if verbose:
      dump_vagrant_data(topology)
    else:
      create_vagrantfile(topology,args.vagrant)

  if args.xpand:
    if args.verbose:
      dump_topology_data(topology,'Augmented')
    else:
      create_topology_file(topology)

  if args.inventory:
    if args.verbose:
      dump_inventory_data(topology,args.hostvars)
    else:
      write_ansible_inventory(topology,args.inventory,args.hostvars)
#    with open(args.inventory,"w") as output:
#      output.write(yaml.dump(create_ansible_inventory(topology['nodes'],defaults,args.hostvars)))

main()