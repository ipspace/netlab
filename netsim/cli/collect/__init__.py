#
# netlab collect command
#
# Collect device configurations
#
import argparse
import concurrent.futures
import os
import pathlib
import subprocess
import sys
import typing

from box import Box

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
from . import netmiko
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

INTERNAL_DISPATCH: dict = {
  'netmiko': netmiko.collect
}

def run_internal(args: argparse.Namespace, topology: Box, output_path: str, nodeset: list, skip_list: list) -> int:

  int_count = 0

  def collect_node(n: str) -> None:
    nonlocal int_count
    for method,callback in INTERNAL_DISPATCH.items():
      try:
        status = callback(n,output_path,suffix,topology)
        if status is not None:
          skip_list.append(n)
          nodeset.remove(n)
          int_count += 1
          break
      except KeyboardInterrupt as ex:
        raise KeyboardInterrupt from ex
      except Exception as ex:
        log.error(
          f'Failed to collect configuration from {n} using {method}',
          more_data=str(ex),
          module='collect')

  suffix = '.' + (args.suffix or 'cfg')
  with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.map(collect_node, list(nodeset))

  return int_count

def run_ansible(args: argparse.Namespace, rest: list, output_path: str, nodeset: list, skip_list: list) -> None:
  args.limit = ','.join(nodeset)
  ansible_args = i_utils.min_ansible_args(args,"dense")
  ansible_args += ['-e',f"target='{output_path}'"]
  if args.suffix:
    ansible_args += ['-e',f"suffix='{args.suffix}'"]

  rest = ansible_args + rest
  if log.VERBOSE:
    print("Ansible playbook args: %s" % rest)

  try:
    i_utils.ansible_skip_group(skip_list)
    ansible.playbook('collect-configs.ansible',rest)
  finally:
    i_utils.ansible_skip_group([])

def run(cli_args: typing.List[str]) -> None:
  run_dir = os.getcwd()
  (args,rest) = collect_parse(cli_args)
  log.set_logging_flags(args)
  set_dry_run(args)
  output_path = str(pathlib.Path(args.output).absolute())
  topology = load_snapshot(args)

  (nodeset,skip_list) = c_utils.collectable(_nodeset.from_args(args,topology,skip_unprovisioned=True),topology)

  if not log.QUIET:
    log.section_header('Collect','Collecting device configurations')

  c_utils.create_output(output_path)
  int_cnt = run_internal(args,topology,output_path,nodeset,skip_list)
  used_ansible = False
  if nodeset:
    if int_cnt and not log.QUIET:
      log.section_header('Collect','Collecting remaining device configurations with Ansible')
    run_ansible(args,rest,output_path,nodeset,skip_list)
    used_ansible = True

  if args.tar:
    log.exit_on_error()
    c_utils.create_tar(args,run_dir)

  if args.tar or used_ansible:
    log.repeat_warnings('netlab collect')
