#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import yaml
import re
from box import Box

from . import common
from . import cli_parser
from . import read_topology
from . import augment
from . import inventory
from .providers import Provider

LOGGING=False
VERBOSE=False

def dump_topology_data(topology,state):
  print("%s topology data" % state)
  print("===============================")

  topo_copy = Box(topology,box_dots=True)

  topo_copy.pop("nodes_map",None)
  print(topo_copy.to_yaml())

def main():
  args = cli_parser.parse()

  topology = read_topology.load(args.topology,args.defaults,"package:topology-defaults.yml")
  if args.verbose:
    dump_topology_data(topology,'Collected')
  common.exit_on_error()

  augment.main.transform(topology)
  common.exit_on_error()
  if args.provider is not None:
    provider = Provider.load(topology.provider,topology.defaults.providers[topology.provider])
    if args.verbose:
      provider.dump(topology)
    else:
      provider.create(topology,args.provider)

  if args.xpand:
    if args.verbose:
      dump_topology_data(topology,'Augmented')
    else:
      augment.topology.create_topology_file(topology,args.xpand)

  if args.inventory:
    if args.verbose:
      inventory.dump(topology)
    else:
      inventory.write(topology,args.inventory,args.hostvars)

  if args.config:
    inventory.config(args.config,args.inventory)
