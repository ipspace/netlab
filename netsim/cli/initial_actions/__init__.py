"""
Common functions for the "netlab initial" actions
"""

import argparse
import os
import typing

from .. import common_parse_args, parser_lab_location
from . import configs


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
    '-l','--limit',
    dest='limit', action='store',
    help='Limit the operation to a subset of nodes')
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
    '--clean',
    dest='clean', action='store_true',
    help='Clean up the output directory before creating the initial configuration')
  parser.add_argument(
    '--no-message',
    dest='no_message', action='store_true',
    help=argparse.SUPPRESS)
  parser_lab_location(parser,instance=True,i_used=True,action='configure')

  return parser.parse_known_args(args)

"""
Build Ansible arguments based on 'netlab initial' parameters
"""
def ansible_args(args: argparse.Namespace) -> list:
  rest: typing.List[str] = []
  if args.verbose:
    rest = ['-' + 'v' * args.verbose] + rest

  if args.limit:
    rest = ['--limit',args.limit] + rest

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

  if args.fast or os.environ.get('NETLAB_FAST_CONFIG',None):
    rest = ['-e','netlab_strategy=free'] + rest

  return rest

def get_deploy_parts(args: argparse.Namespace) -> list:
  deploy_parts = []
  if args.initial:
    deploy_parts.append("initial configuration")

  if args.module:
    if args.module != "*":
      deploy_parts.append("module(s): " + args.module)
    else:
      deploy_parts.append("modules")

  if args.custom:
    deploy_parts.append("custom")

  return deploy_parts
