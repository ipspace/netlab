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

import common
import argparse
import read_topology
import augment.main
import inventory
import provider
import utils

def create_expected_results_file(topology,fname):
  with open(fname,"w") as output:
    output.write(utils.transformation_results_yaml(topology))
    output.close()
    print("Created expected transformed topology: %s" % fname)

def parse():
  parser = argparse.ArgumentParser(description='Create topology test cases')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file name')
  parser.add_argument('--defaults', dest='defaults', action='store', default='../topology-defaults.yml',
                  help='Topology defaults file')
  parser.add_argument('-x','--expanded', dest='xpand', action='store', nargs='?', const='exp-topology.yml',
                  help='Expected topology file name')
  args = parser.parse_args()

  common.VERBOSE = False
  common.LOGGING = True
  return args

def main():
  args = parse()
  topology = read_topology.load(args.topology,None,args.defaults)
  common.exit_on_error()
  augment.main.transform(topology)
  common.exit_on_error()

  dfname = args.xpand or ("exp-"+args.topology)
  create_expected_results_file(topology,dfname)

main()
