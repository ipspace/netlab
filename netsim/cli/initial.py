#
# netlab initial command
#
# Deploys initial device configurations
#
import typing
import os
import argparse

from . import common_parse_args
from . import ansible
from .. import set_logging_flags

#
# CLI parser for 'netlab initial' command
#
def initial_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args() ],
    prog="netlab initial",
    description='Initial device configurations',
    epilog='All other arguments are passed directly to ansible-playbook')

  parser.add_argument(
    '-i','--initial',
    dest='initial', action='store_true',
    help='Deploy just the initial configuration')
  parser.add_argument(
    '-m','--module',
    dest='module', action='store',nargs='?',const='*',
    help='Deploy module-specific configuration (optionally including a list of modules separated by commas)')
  parser.add_argument(
    '-o','--output',
    dest='output', action='store',nargs='?',const='config',
    help='Create a directory with initial configurations instead of deploying them (default output directory: config)')
  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)

  if args.verbose:
    rest = ['-v'] + rest

  if args.initial:
    rest = ['-t','initial'] + rest

  if args.module:
    if args.module != "*":
      rest = ['-e','modlist='+args.module] + rest
    rest = ['-t','module'] + rest
  
  if args.output:
    rest = ['-e','config='+os.path.abspath(args.output) ]

  if args.logging or args.verbose:
    print("Ansible playbook args: %s" % rest)

  if args.output:
    ansible.playbook('create-config.ansible',rest)
    print("\nInitial configurations have been created in the %s directory" % args.output)
  else:
    ansible.playbook('initial-config.ansible',rest)
