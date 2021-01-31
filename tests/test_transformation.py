#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import glob
import pathlib

import common
import read_topology
import augment.main
import utils

def create_expected_results_file(topology,fname):
  with open(fname,"w") as output:
    output.write(utils.transformation_results_yaml(topology))
    output.close()
    print("Created expected transformed topology: %s" % fname)

def test_transformation_cases():
  print("Starting transformation test cases")
  for test_case in list(glob.glob('topology*yml')):
    print("Test case: %s" % test_case)
    topology = read_topology.load(test_case,None,"../topology-defaults.yml")
    common.exit_on_error()
    augment.main.transform(topology)
    common.exit_on_error()

    result = utils.transformation_results_yaml(topology)
    expected = pathlib.Path('exp-'+test_case).read_text()
    assert result == expected
    print("... succeeded, string length = %d" % len(result))

test_transformation_cases()
