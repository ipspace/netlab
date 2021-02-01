#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import yaml
import pathlib
import difflib

import common
import argparse
import read_topology
import augment.main
import inventory
import provider
import utils

def parse():
  parser = argparse.ArgumentParser(description='Create topology test cases')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file name')
  parser.add_argument('--defaults', dest='defaults', action='store', default='../topology-defaults.yml',
                  help='Topology defaults file')
  parser.add_argument('-x','--expected', dest='xpand', action='store', nargs='?', const='exp-topology.yml',
                  help='Expected topology file name')
  args = parser.parse_args()

  common.VERBOSE = False
  common.LOGGING = False
  return args

def main():
  args = parse()
  topology = read_topology.load(args.topology,None,args.defaults)
  common.exit_on_error()
  augment.main.transform(topology)
  common.exit_on_error()

  result = utils.transformation_results_yaml(topology)
  expected = pathlib.Path('exp-'+args.topology).read_text()
  if result == expected:
    print("Results match")
  else:
    print('\n'.join(list(difflib.unified_diff(expected.split('\n'),result.split('\n'),fromfile='expected',tofile='actual'))))

main()
