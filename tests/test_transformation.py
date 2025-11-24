#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import difflib
import glob
import pathlib
import sys

import pytest
import utils
from box import Box

from netsim import augment
from netsim.outputs import _TopologyOutput, ansible
from netsim.utils import log
from netsim.utils import read as _read


def run_test(fname):
  log.init_log_system(header = False)
  topology = _read.load(fname,relative_topo_name=True,user_defaults=[])
  log.exit_on_error()
  augment.main.transform(topology)
  log.exit_on_error()
  return topology

def run_transformation_test(test_case: str, tmpdir: str = '/tmp'):
  print("Test case: %s" % test_case)
  log.set_flag(raise_error = False)
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
  exp_test_case = test_case.replace("/input/","/expected/")
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
  
@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_xform_cases(tmpdir):
  print("Starting transformation test cases")
  for test_case in list(glob.glob('topology/input/*yml')):
    run_transformation_test(test_case)

# Verbose test cases are executed only when we're doing a coverage report
#
def test_coverage_verbose_cases(tmpdir):
  if not sys.gettrace():
    return
  log.set_verbose()
  test_xform_cases(tmpdir)

def run_error_case(test_case: str) -> None:
  log.set_flag(raise_error = True)
  print("Test case: %s" % test_case)
  log.err_count = 0
  with pytest.raises(log.ErrorAbort):
    run_test(test_case)

  error_log = log.get_error_log()
  log_file = pathlib.Path(test_case.replace('.yml','.log'))
  if log_file.exists():
    with log_file.open() as f:
      log_lines = [line.rstrip('\n') for line in f]

    if error_log != log_lines:
      error_log_text = "\n".join(error_log)
      expected_text  = "\n".join(log_lines)
      print(f'Accumulated error log\n{"=" * 70}\n{error_log_text}\n\nExpected log\n{"=" * 70}\n{expected_text}')
    assert error_log == log_lines

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_error_cases():
  print("Starting error test cases")
  for test_case in list(glob.glob('errors/*yml')):
    run_error_case(test_case)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_coverage_xf_cases():
  for test_case in list(glob.glob('coverage/input/*yml')):
    run_transformation_test(test_case)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
def test_coverage_errors():
  for test_case in list(glob.glob('coverage/errors/*yml')):
    run_error_case(test_case)

if __name__ == "__main__":
  test_xform_cases("/tmp")
#  test_error_cases()
#  test_minimal_cases()
