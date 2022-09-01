#
# netlab initial command
#
# Deploys initial device configurations
#
import typing
import os
import argparse

from . import common_parse_args,get_message,load_snapshot_or_topology
from . import ansible
from box import Box

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
    '-c','--custom',
    dest='custom', action='store_true',
    help='Deploy custom configuration templates (specified in "config" group or node attribute)')
  parser.add_argument(
    '--fast',
    dest='fast', action='store_true',
    help='Use "free" strategy in Ansible playbook for faster configuration deployment')
  parser.add_argument(
    '-o','--output',
    dest='output', action='store',nargs='?',const='config',
    help='Create a directory with initial configurations instead of deploying them (default output directory: config)')
  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)

  if args.verbose:
    rest = ['-' + 'v' * args.verbose] + rest

  if args.initial:
    rest = ['-t','initial'] + rest

  if args.quiet:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  if args.module:
    if args.module != "*":
      rest = ['-e','modlist='+args.module] + rest
    rest = ['-t','module'] + rest
  
  if args.custom:
    rest = ['-t','custom'] + rest

  if args.output:
    rest = ['-e','config_dir='+os.path.abspath(args.output) ]

  if args.fast or os.environ.get('NETLAB_FAST_CONFIG',None):
    rest = ['-e','netlab_strategy=free']

  if args.logging or args.verbose:
    print("Ansible playbook args: %s" % rest)

  if args.output:
    ansible.playbook('create-config.ansible',rest)
    print("\nInitial configurations have been created in the %s directory" % args.output)
  else:
    ansible.playbook('initial-config.ansible',rest)
    topology = load_snapshot_or_topology(Box({},default_box=True,box_dots=True))
    if topology:
      message = get_message(topology,'initial',True)
      if message:
        print(f"\n\n{message}")
