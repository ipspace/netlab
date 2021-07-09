#
# netlab collect command
#
# Collect device configurations
#
import typing
import os
import argparse

from . import common_parse_args
from . import ansible
from .. import set_logging_flags

#
# CLI parser for 'netlab collect' command
#
def initial_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab collect",
    description='Collect device configurations',
    epilog='All other arguments are passed directly to ansible-playbook')

  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    '-o','--output',
    dest='output',
    action='store',
    nargs='?',
    default='config',
    help='Output directory (default: config)')
  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)

  if args.verbose:
    rest = ['-v'] + rest

  rest = ['-e','target='+args.output ] + rest

  if args.verbose:
    print("Ansible playbook args: %s" % rest)

  ansible.playbook('collect-configs.ansible',rest)
