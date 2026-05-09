#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import argparse
import sys

import utils
from box import Box

import netsim.augment
from netsim.data import get_box
from netsim.utils import log
from netsim.utils import read as _read


def create_expected_results_file(topology: Box,fname: str) -> None:
  with open(fname,"w") as output:
    output.write(utils.transformation_results_yaml(topology))
    output.close()
    print(f"... created expected transformed topology: {fname}")

def parse() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description='Create topology test cases')
  parser.add_argument('-t','--topology', dest='topology', action='store', default='topology.yml',
                  help='Topology file name')
  parser.add_argument('--defaults', dest='defaults', action='store', help='Topology defaults file')
  parser.add_argument('-x','--expanded', dest='xpand', action='store', nargs='?', const='exp-topology.yml',
                  help='Expected topology file name')
  args = parser.parse_args()

  return args

def main() -> None:
  args = parse()
  if utils.HAS_RUAMEL:
    print(
      "WARNING: ruamel.yaml is installed; fixture generation will be slower. "
      "Consider uninstalling ruamel.yaml (see #3345).",
      file=sys.stderr,
    )
  print(f"Reading {args.topology}")
  topology = _read.load(args.topology,user_defaults=[],relative_topo_name=True)
  if utils.HAS_RUAMEL:
    topology = get_box(utils.clean_ruamel(topology))
  log.exit_on_error()
  netsim.augment.main.transform(topology)
  log.exit_on_error()

  dfname = args.xpand or (args.topology.replace("/input/","/expected/"))
  create_expected_results_file(topology,dfname)

main()
