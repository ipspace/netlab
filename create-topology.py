#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import yaml
import re
from jinja2 import Environment, FileSystemLoader, Undefined, StrictUndefined, make_logging_undefined

sys.path[0] = sys.path[0] + '/create-topology'

import common
import cli_parser
import read_topology
import augment
import inventory

LOGGING=False
VERBOSE=False


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

def dump_vagrant_data(topology,path):
  print("\nVagrantfile")
  print("============================")
  print(common.template('Vagrantfile.j2',topology,path))

def create_vagrantfile(topology,fname,path):
  with open(fname,"w") as output:
    output.write(common.template('Vagrantfile.j2',topology,path))
    output.close()
    print("Created Vagrantfile: %s" % fname)

def main():
  args = cli_parser.parse()

  path = os.path.dirname(os.path.realpath(__file__))
  settings = path+"/topology-defaults.yml"
  topology = read_topology.load(args.topology,args.defaults,settings)
  if args.verbose:
    dump_topology_data(topology,'Collected')
  common.exit_on_error()

  augment.augment(topology)
  if args.vagrant:
    if args.verbose:
      dump_vagrant_data(topology,path)
    else:
      create_vagrantfile(topology,args.vagrant,path)

  if args.xpand:
    if args.verbose:
      dump_topology_data(topology,'Augmented')
    else:
      create_topology_file(topology)

  if args.inventory:
    if args.verbose:
      inventory.dump(topology)
    else:
      inventory.write(topology,args.inventory,args.hostvars)
#    with open(args.inventory,"w") as output:
#      output.write(yaml.dump(create_ansible_inventory(topology['nodes'],defaults,args.hostvars)))

main()