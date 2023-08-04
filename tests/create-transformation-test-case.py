#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import yaml
import re
import argparse
from jinja2 import Environment, FileSystemLoader, Undefined, StrictUndefined, make_logging_undefined

import netsim.common
import netsim.read_topology
import netsim.augment
import utils

def create_expected_results_file(topology,fname):
  with open(fname,"w") as output:
    output.write(utils.transformation_results_yaml(topology))
    output.close()
    print(f"... created expected transformed topology: {fname}")

def parse():
  parser = argparse.ArgumentParser(description='Create topology test cases')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file name')
  parser.add_argument('--defaults', dest='defaults', action='store', help='Topology defaults file')
  parser.add_argument('-x','--expanded', dest='xpand', action='store', nargs='?', const='exp-topology.yml',
                  help='Expected topology file name')
  args = parser.parse_args()

  return args

def main():
  args = parse()
  print(f"Reading {args.topology}")
  topology = netsim.read_topology.load(args.topology,args.defaults,"package:topology-defaults.yml")
  netsim.log.exit_on_error()
  netsim.augment.main.transform(topology)
  netsim.log.exit_on_error()

  dfname = args.xpand or (args.topology.replace("/input/","/expected/"))
  create_expected_results_file(topology,dfname)

main()
