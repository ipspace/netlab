#
# Parser and related functions for the "netlab validate" command
#
import argparse
import re
import typing

from box import Box

from ...utils import log
from .. import parser_add_debug, parser_add_verbose, parser_lab_location


#
# CLI parser for 'netlab validate' command
#
def validate_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab validate",
    description='Run lab validation tests specified in the lab topology')
  parser_add_debug(parser)                                # Add debugging/test options
  parser_add_verbose(parser)                              # ... and verbosity flag
  parser.add_argument(
    '--list',
    dest='list',
    action='store_true',
    help='List validation tests')
  parser.add_argument(
    '--node',
    dest='nodes', action='store',
    help='Execute validation tests only on selected node(s)')
  parser.add_argument(
    '--skip-wait',
    dest='nowait', action='store_true',
    help='Skip the waiting period')
  parser.add_argument(
    '-e','--error-only',
    dest='error_only', action='store_true',
    help='Display only validation errors (on stderr)')
  parser.add_argument(
    '--source',
    dest='test_source',action='store',
    help='Read tests from the specified YAML file')
  parser.add_argument(
    '--skip-missing',
    dest='skip_missing', action='store_true',
    help=argparse.SUPPRESS)
  parser.add_argument(
    '--dump',
    action='store',
    choices=['result'],
    nargs='+',
    default=[],
    help='Dump additional information during the validation process')
  parser.add_argument(
    dest='tests', action='store',
    nargs='*',
    help='Validation test(s) to execute (default: all)')
  parser_lab_location(parser,instance=True,action='validate')

  return parser.parse_args(args)

'''
filter_by_test: select only tests specified in arguments
'''
def filter_by_tests(args: argparse.Namespace, topology: Box) -> None:
  if not args.tests:
    return
  tests_to_execute = {}
  for t in args.tests:
    find_test = { v_entry.name: v_entry for v_entry in topology.validate if re.fullmatch(t,v_entry.name) }
    if not find_test:
      log.error(
        f'Invalid test name or regex expression {t}, use "netlab validate --list" to list test names',
        category=log.IncorrectValue,
        module='validation')
    tests_to_execute.update(find_test)

  if log.pending_errors():
    return

  topology.validate = tests_to_execute.values()

'''
filter_by_nodes: select only tests executed on specified node
'''
def filter_by_nodes(args: argparse.Namespace, topology: Box) -> None:
  if not args.nodes:
    return

  node_list = args.nodes.split(',')
  node_set  = set(node_list)

  for n in node_list:
    if not n in topology.nodes:
      log.error(
        f'Invalid node name {n}, use "netlab inspect nodes" to list nodes in your lab',
        category=log.IncorrectValue,
        module='validation')

  if log.pending_errors():
    return

  topology.validate = [ v_entry for v_entry in topology.validate if set(v_entry.nodes) & node_set ]
  if not topology.validate:
    log.error(
      f'No tests are executed on any of the specified nodes',
      category=log.IncorrectValue,
      module='validation')
    return

  for v_entry in topology.validate:
    v_entry.nodes = [ n for n in v_entry.nodes if n in node_list ]
