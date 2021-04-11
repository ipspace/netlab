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

import utils

from netsim import common
from netsim import read_topology
from netsim import augment

def run_test(fname,local_defaults="topology-defaults.yml"):
  topology = read_topology.load(fname,local_defaults,"package:topology-defaults.yml")
  common.exit_on_error()
  augment.main.transform(topology)
  common.exit_on_error()
  return topology

def test_transformation_cases():
  print("Starting transformation test cases")
  for test_case in list(glob.glob('topology/input/*yml')):
    print("Test case: %s" % test_case)
    topology = run_test(test_case)

    result = utils.transformation_results_yaml(topology)
    exp_test_case = "topology/expected/"+os.path.basename(test_case)
    expected = pathlib.Path(exp_test_case).read_text()
    assert result == expected
    print("... succeeded, string length = %d" % len(result))

@pytest.mark.filterwarnings("ignore:api v1")
def test_error_cases():
  print("Starting error test cases")
  common.RAISE_ON_ERROR = True
  for test_case in list(glob.glob('errors/*yml')):
    print("Test case: %s" % test_case)
    common.err_count = 0
    with pytest.raises(common.FatalError):
      run_test(test_case)

test_transformation_cases()
