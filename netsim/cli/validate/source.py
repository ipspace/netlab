#
# Read an alternate validation file specified in the 'netlab validate --source' parameter
#


import os

from box import Box

from ...augment import validate as _validate
from ...data import global_vars
from ...data.types import must_be_id
from ...data.validate import init_validation, validate_attributes
from ...utils import log, read
from .. import error_and_exit


def validate_test_attributes(topology: Box) -> None:
  for t_name,t_data in topology.validate.items():
    must_be_id(
      parent=None,
      key=t_name,
      path=f'NOATTR:test name {t_name}',
      module='validate')
    validate_attributes(
      data=t_data,                                    # Validate test description
      topology=topology,
      data_path=f'validate.{t_name}',                 # Topology path to test entry
      data_name=f'validation test',
      attr_list=['_v_entry'],                         # We're checking validation entries
      module='validate')                              # Function is called from 'validate' command

  log.exit_on_error()

def update_validation_tests(topology: Box, src: str) -> None:
  if not os.path.exists(src):
    error_and_exit(f'{src} does not exist')
  log.info(f'Reading validation tests from {src}')
  add_topo = read.read_yaml(filename=src)         # Read tests or whole topology from input file
  if add_topo is None:
    error_and_exit(f'The input file ({src}) is not a YAML file')
  if not isinstance(add_topo,Box):                # We have to redo most of the sanity checks done by 'netlab create'
    error_and_exit(f'The input file ({src}) is not a dictionary')

  if 'validate' in add_topo:                      # If we have a 'validate' element in the input dictionary
    v_tests = add_topo.validate                   # We're assuming we read a whole lab topology
    if not isinstance(v_tests,Box):               # ... and validate element must be a dictionary
      error_and_exit('The "validate" element in the input file is not a dictionary')
  else:
    v_tests = add_topo                            # Maybe we just read the tests source file?

  if 'nodes' in v_tests or 'links' in v_tests:    # Anyway, final bit of a sanity check...
    error_and_exit(                               # ... maybe we got a topology file with no 'validate' element?
      'The source file contains "nodes" or "links" but no "validate" element',
      more_hints="It looks like your topology file has no validation tests")

  topology.validate = v_tests                     # Hope we got it right; replace validation tests
  global_vars.init(topology)
  init_validation(topology)
  validate_test_attributes(topology)
  _validate.process_validation(topology)          # Do checks and data transformation on validation tests

  return
