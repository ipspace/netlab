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
import difflib
from box import Box

import utils

from netsim import common
from netsim import read_topology
from netsim import augment
from netsim.outputs import _TopologyOutput,ansible

def run_test(fname,local_defaults="topology-defaults.yml",sys_defaults="package:topology-defaults.yml"):
  topology = read_topology.load(fname,local_defaults,sys_defaults)
  common.exit_on_error()
  augment.main.transform(topology)
  common.exit_on_error()
  return topology

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_transformation_cases(tmpdir):
  print("Starting transformation test cases")
  for test_case in list(glob.glob('topology/input/*yml')):
    print("Test case: %s" % test_case)
    topology = run_test(test_case)

    if topology.defaults.get("inventory"):
      print("Writing inventory... %s" % topology.defaults.inventory)
      ansible.ansible_inventory(topology,tmpdir+"/extra/hosts.yml",topology.defaults.get("inventory").replace("dump",""))
      ansible.ansible_config(tmpdir+"/ansible.cfg",tmpdir+"/hosts.yml")
      if topology.defaults.inventory == "dump":
        ansible.dump(topology)

    if topology.defaults.get("Output"):
      for output_format in topology.defaults.get("Output"):
        output_module = _TopologyOutput.load(output_format,topology.defaults.outputs[output_format])
        if output_module:
          output_module.write(Box(topology))
        else:
          common.error('Unknown output format %s' % output_format,common.IncorrectValue,'create')

    result = utils.transformation_results_yaml(topology)
    exp_test_case = "topology/expected/"+os.path.basename(test_case)
    expected = pathlib.Path(exp_test_case).read_text()
    if result != expected:
      print("Test case: %s FAILED" % test_case)
      sys.stdout.writelines(
        difflib.unified_diff(
          expected.splitlines(keepends=True),
          result.splitlines(keepends=True),
          fromfile='expected',tofile='result'))

    assert result == expected
    print("... succeeded, string length = %d" % len(result))

# Verbose test cases are executed only when we're doing a coverage report
#
def test_verbose_cases(tmpdir):
  if not sys.gettrace():
    return
  common.set_verbose()
  test_transformation_cases(tmpdir)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_error_cases():
  print("Starting error test cases")
  common.set_flag(raise_error = True)
  for test_case in list(glob.glob('errors/*yml')):
    print("Test case: %s" % test_case)
    common.err_count = 0
    with pytest.raises(common.ErrorAbort):
      topo = run_test(test_case)

"""
With the expanded default settings, it became impractical to run test cases
without the defaults. These test cases have been migrated into errors

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_minimal_cases():
  print("Starting minimal (no-default) test cases")
  common.set_flag(raise_error = True)
  for test_case in list(glob.glob('minimal_errors/*yml')):
    print("Test case: %s" % test_case)
    common.err_count = 0
    with pytest.raises(common.ErrorAbort):
      run_test(test_case,None,None)
"""

if __name__ == "__main__":
  test_transformation_cases("/tmp")
#  test_error_cases()
#  test_minimal_cases()
