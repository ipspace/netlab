"""
Common functions for the "netlab initial" actions
"""

import argparse
import os
import typing

from box import Box

from .. import common_parse_args, parser_lab_location


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

"""
Get the list of modules deployed
"""
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

"""
node_deploy_list -- FIgure out what needs to be deployed on the node
based on CLI arguments
"""
def node_deploy_list(node: Box, args: argparse.Namespace) -> list:
  all_config = not args.module and not args.initial and not args.custom

  node_configs = []
  if args.module or all_config:
    node_modules = node.get('module',[])
    if args.module == '*' or all_config:
      node_configs = node_modules
    else:
      node_configs = [ m for m in args.module.split(',') if m in node_modules ]
  if args.initial or all_config:
    node_configs = ['initial'] + node_configs
  if args.custom or all_config:
    node_configs += node.get('config',[])

  return node_configs

"""
node_requires_ansible: Figure out whether the node needs deployment through
an Ansible playbook based on what the user wants configured
"""
def node_requires_ansible(node: Box, args: argparse.Namespace) -> bool:
  n_deploy = node_deploy_list(node,args)
  n_skip   = node.get('netlab_ansible_skip_module',[])
  return bool(set(n_deploy) - set(n_skip))

"""
nodeset_requires_ansible: Does any node in the nodeseet need deployment through
an Ansible playbook?
"""
def nodeset_requires_ansible(nodeset: list, topology: Box, args: argparse.Namespace) -> bool:
  for n_name in nodeset:
    n_data = topology.nodes.get(n_name,{})
    if node_requires_ansible(n_data,args):
      return True

  return False
