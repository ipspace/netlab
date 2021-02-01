#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import sys
import os
import glob
import pathlib
import pytest

import common
import read_topology
import augment.main
import utils

def run_test(fname,local_defaults="topology-defaults.yml"):
  topology = read_topology.load(fname,local_defaults,"../topology-defaults.yml")
  common.exit_on_error()
  augment.main.transform(topology)
  common.exit_on_error()
  return topology

def test_transformation_cases():
  print("Starting transformation test cases")
  for test_case in list(glob.glob('topology*yml')):
    print("Test case: %s" % test_case)
    topology = run_test(test_case)

    result = utils.transformation_results_yaml(topology)
    expected = pathlib.Path('exp-'+test_case).read_text()
    assert result == expected
    print("... succeeded, string length = %d" % len(result))

@pytest.mark.filterwarnings("ignore:api v1")
def test_error_cases():
  print("Starting error test cases")
  common.RAISE_ON_ERROR = True
  for test_case in list(glob.glob('err*yml')):
    print("Test case: %s" % test_case)
    common.err_count = 0
    with pytest.raises(common.FatalError):
      topology = run_test(test_case)

test_transformation_cases()
