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

from netsim.utils import log,strings,read as _read
from netsim import augment
from netsim.outputs import _TopologyOutput,ansible

def run_test(fname):
  topology = _read.load(fname,relative_topo_name=True)
  log.exit_on_error()
  augment.main.transform(topology)
  log.exit_on_error()
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
          log.error('Unknown output format %s' % output_format,log.IncorrectValue,'create')

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
  log.set_verbose()
  test_transformation_cases(tmpdir)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_error_cases():
  print("Starting error test cases")
  log.set_flag(raise_error = True)
  for test_case in list(glob.glob('errors/*yml')):
    print("Test case: %s" % test_case)
    log.err_count = 0
    with pytest.raises(log.ErrorAbort):
      topo = run_test(test_case)

if __name__ == "__main__":
  test_transformation_cases("/tmp")
#  test_error_cases()
#  test_minimal_cases()
