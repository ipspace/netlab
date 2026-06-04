#!/usr/bin/env python3
#
# Create expanded topology file, Ansible inventory, host vars, or Vagrantfile from
# topology file
#

import contextlib
import difflib
import glob
import io
import os
import pathlib
import sys
import typing

import pytest
import utils
from box import Box

from netsim import augment
from netsim.data import get_box
from netsim.outputs import _TopologyOutput, ansible
from netsim.utils import log
from netsim.utils import read as _read


def run_test(fname: str) -> Box:
  log.init_log_system(header = False)
  topology = _read.load(fname,relative_topo_name=True,user_defaults=[])
  if utils.HAS_RUAMEL:
    topology = get_box(utils.clean_ruamel(topology))
  log.exit_on_error()
  augment.main.transform(topology)
  log.exit_on_error()
  return topology

def transformation_results(test_case: str, tmp_path: pathlib.Path) -> typing.Tuple[str,str]:
  log.set_flag(raise_error = False)
  topology = run_test(test_case)

  # All side-effect file writes (Ansible inventory, output modules, the
  # group_vars/ and host_vars/ trees that ansible_inventory creates with
  # CWD-relative paths) land inside tmp_path, isolating each case from
  # every other one and from the tests/ directory.
  cwd = os.getcwd()
  os.chdir(tmp_path)
  try:
    if topology.defaults.get("inventory"):
      ansible.ansible_inventory(topology,"hosts.yml",topology.defaults.get("inventory").replace("dump",""))
      ansible.ansible_config("ansible.cfg","hosts.yml")
      if topology.defaults.inventory == "dump":
        ansible.dump(topology)

    if topology.defaults.get("Output"):
      for output_format in topology.defaults.get("Output"):
        output_module = _TopologyOutput.load(output_format,topology.defaults.outputs[output_format])
        if output_module:
          output_module.write(Box(topology))
        else:
          log.error('Unknown output format %s' % output_format,log.IncorrectValue,'create')
  finally:
    os.chdir(cwd)

  result = utils.transformation_results_yaml(topology)
  exp_test_case = test_case.replace("/input/","/expected/")
  expected = pathlib.Path(exp_test_case).read_text()

  return (result,expected)

def report_mismatch(test_case: str, label: str, actual: str, expected: str) -> None:
  if actual == expected:
    return

  diff = "".join(
    difflib.unified_diff(
      expected.splitlines(keepends=True),
      actual.splitlines(keepends=True),
      fromfile="expected",
      tofile="actual"))
  pytest.fail(f"{label} mismatch for {test_case}\n{diff}",pytrace=False)

def run_transformation_test(test_case: str, tmp_path: pathlib.Path) -> None:
  (result,expected) = transformation_results(test_case,tmp_path)
  report_mismatch(test_case,"transformation",result,expected)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
@pytest.mark.parametrize('test_case',sorted(glob.glob('topology/input/*yml')))
def test_xform_cases(test_case: str, tmp_path: pathlib.Path) -> None:
  run_transformation_test(test_case,tmp_path)

# Verbose test cases are executed only when we're running under coverage
# (sys.gettrace() returns the tracer); skipped otherwise so the result is
# visibly SKIPPED instead of silently PASSED.
#
# Each inner iteration gets its own scratch dir via tmp_path_factory.mktemp()
# so coverage measurement stays deterministic with respect to filesystem
# state -- output modules with create-if-missing branches would otherwise
# exercise different code paths depending on iteration order.
#
@pytest.mark.skipif(not sys.gettrace(),reason="coverage-only test")
def test_coverage_verbose_cases(tmp_path_factory: pytest.TempPathFactory) -> None:
  log.set_verbose()
  for test_case in sorted(glob.glob('topology/input/*yml')):
    run_transformation_test(test_case,tmp_path_factory.mktemp("coverage"))

def error_results(test_case: str) -> typing.Tuple[str, str]:
  log.set_flag(raise_error = True)
  with pytest.raises(log.ErrorAbort):
    with contextlib.redirect_stderr(io.StringIO()) as _:
      run_test(test_case)

  error_log = '\n'.join(log.get_error_log())
  log_file = pathlib.Path(test_case.replace('.yml','.log'))
  expected_log = log_file.read_text().strip('\n') if log_file.exists() else ""
  return (error_log,expected_log)
  
def run_error_case(test_case: str) -> None:
  (error_log,expected_log) = error_results(test_case)
  report_mismatch(test_case,"error-log",error_log,expected_log)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
@pytest.mark.parametrize('test_case',sorted(glob.glob('errors/*yml')))
def test_error_cases(test_case: str) -> None:
  run_error_case(test_case)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
@pytest.mark.parametrize('test_case',sorted(glob.glob('coverage/input/*yml')))
def test_coverage_xf_cases(test_case: str, tmp_path: pathlib.Path) -> None:
  run_transformation_test(test_case,tmp_path)

@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
@pytest.mark.parametrize('test_case',sorted(glob.glob('coverage/errors/*yml')))
def test_coverage_errors(test_case: str) -> None:
  run_error_case(test_case)
