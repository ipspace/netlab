#
# netlab initial command
#
# Deploys initial device configurations
#
import typing
import os
import argparse

from . import common_parse_args,get_message,load_snapshot_or_topology,lab_status_change
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
  parser.add_argument(
    '--no-message',
    dest='no_message', action='store_true',
    help=argparse.SUPPRESS)
  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)

  deploy_parts = []
  if args.verbose:
    rest = ['-' + 'v' * args.verbose] + rest

  if args.initial:
    rest = ['-t','initial'] + rest
    deploy_parts.append("initial configuration")

  if args.quiet:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  if args.module:
    if args.module != "*":
      deploy_parts.append("module(s): " + args.module)
      rest = ['-e','modlist='+args.module] + rest
    else:
      deploy_parts.append("modules")
    rest = ['-t','module'] + rest
  
  if args.custom:
    deploy_parts.append("custom")
    rest = ['-t','custom'] + rest

  if args.output:
    rest = ['-e','config_dir='+os.path.abspath(args.output) ] + rest

  if args.fast or os.environ.get('NETLAB_FAST_CONFIG',None):
    rest = ['-e','netlab_strategy=free'] + rest

  if args.logging or args.verbose:
    print("Ansible playbook args: %s" % rest)

  if args.output:
    ansible.playbook('create-config.ansible',rest)
    print("\nInitial configurations have been created in the %s directory" % args.output)
  else:
    topology = load_snapshot_or_topology(Box({},default_box=True,box_dots=True))
    deploy_text = ', '.join(deploy_parts) or 'complete configuration'
    if not topology is None:
      lab_status_change(topology,f'deploying configuration: {deploy_text}')

    ansible.playbook('initial-config.ansible',rest)
    if topology and not args.no_message:
      message = get_message(topology,'initial',True)
      if message:
        print(f"\n\n{message}")
      lab_status_change(topology,f'configuration deployment complete')
