#
# netlab collect command
#
# Collect device configurations
#
import argparse
import os
import pathlib
import subprocess
import sys
import typing

from ...utils import log
from .. import (
  _nodeset,
  ansible,
  error_and_exit,
  external_commands,
  fs_cleanup,
  load_snapshot,
  parser_add_verbose,
  parser_lab_location,
  set_dry_run,
)
from ..initial import utils as i_utils
from . import utils as c_utils


#
# CLI parser for 'netlab collect' command
#
def collect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab collect",
    description='Collect device configurations',
    epilog='All other arguments are passed directly to ansible-playbook')

  parser_add_verbose(parser,verbose=True,quiet=True)
  parser.add_argument(
    '-o','--output',
    dest='output',
    action='store',
    nargs='?',
    default='config',
    help='Output directory (default: config)')
  parser.add_argument(
    '-l','--limit',
    dest='limit', action='store',
    help='Limit the operation to a subset of nodes')
  parser.add_argument(
    '--suffix',
    dest='suffix',
    action='store',
    default='cfg',
    help='Configure file(s) suffix (default: cfg)')
  parser.add_argument(
    '--tar',
    dest='tar',
    action='store',
    help='Create configuration tarball')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Clean up config directory and modified configuration file after creating tarball')
  parser.add_argument(
    '--fast',
    dest='fast', action='store_true',
    help=argparse.SUPPRESS)
  parser_lab_location(parser,instance=True,action='collect configuration from')

  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  run_dir = os.getcwd()
  (args,rest) = collect_parse(cli_args)
  log.set_logging_flags(args)
  set_dry_run(args)
  output_path = str(pathlib.Path(args.output).absolute())
  topology = load_snapshot(args)

  (nodeset,skip_list) = c_utils.collectable(_nodeset.from_args(args,topology,skip_unprovisioned=True),topology)
  c_utils.create_output(output_path)

  args.limit = ','.join(nodeset)
  ansible_args = i_utils.min_ansible_args(args,"dense")
  ansible_args += ['-e',f"target='{output_path}'"]
  if args.suffix:
    ansible_args += ['-e',f"suffix='{args.suffix}'"]

  rest = ansible_args + rest
  if args.verbose:
    print("Ansible playbook args: %s" % rest)

  if not args.quiet:
    log.section_header('Collect','Collecting device configurations')

  OK = False
  try:
    i_utils.ansible_skip_group(skip_list)
    OK = ansible.playbook('collect-configs.ansible',rest)
  finally:
    i_utils.ansible_skip_group([])

  if not OK:
    sys.exit(1)

  if args.tar:
    c_utils.create_tar(args,run_dir)

  log.repeat_warnings('netlab collect')
