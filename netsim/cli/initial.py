#
# netlab initial command
#
# Deploys initial device configurations
#
import argparse
import os
import typing

from .. import devices
from ..utils import log
from ..utils import status as _status
from . import (
  ansible,
  common_parse_args,
  external_commands,
  get_message,
  lab_status_change,
  load_snapshot,
  parser_lab_location,
)


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
    '--ready',
    dest='ready', action='store_true',
    help='Wait for devices to become ready')
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
  parser_lab_location(parser,instance=True,i_used=True,action='configure')

  return parser.parse_known_args(args)

def run_initial(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)
  if args.output:
    rest = ['-e',f'config_dir="{os.path.abspath(args.output)}"' ] + rest

  topology = load_snapshot(args)

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

  if args.fast or os.environ.get('NETLAB_FAST_CONFIG',None):
    rest = ['-e','netlab_strategy=free'] + rest

  if args.logging or args.verbose:
    print("Ansible playbook args: %s" % rest)

  ansible.check_version()
  if args.output:
    ansible.playbook('create-config.ansible',rest)
    print("\nInitial configurations have been created in the %s directory" % args.output)
    return
  elif args.ready:
    ansible.playbook('device-ready.ansible',rest)
    if topology:
      lab_status_change(topology,'devices are ready')
  else:
    external_commands.LOG_COMMANDS = True
    deploy_text = ', '.join(deploy_parts) or 'complete configuration'
    if topology is not None:
      devices.process_config_sw_check(topology)
      lab_status_change(topology,f'deploying configuration: {deploy_text}')

    ansible.playbook('initial-config.ansible',rest)
    if topology and not args.no_message:
      message = get_message(topology,'initial',True)
      if message:
        print(f"\n\n{message}")
      lab_status_change(topology,f'configuration deployment complete')

  if _status.is_directory_locked():                   # If we're using the lock file, touch it after we're done
    _status.lock_directory()                          # .. to have a timestamp of when the lab was started

  log.repeat_warnings('netlab initial')

def run(cli_args: typing.List[str]) -> None:
  try:
    run_initial(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab initial')
