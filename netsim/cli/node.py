#
# netlab node command
#
# Start, stop, restart, pause, or unpause individual lab nodes without touching the rest of the lab
#
import argparse
import typing

from ..providers import execute_node
from ..utils import log
from . import _nodeset, external_commands, load_snapshot, parser_add_verbose, parser_lab_location, set_dry_run


#
# CLI parser for 'netlab node' command
#
def node_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab node",
    description='Start, stop, restart, pause, or unpause individual lab nodes')
  parser_add_verbose(parser,quiet=True)
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help='Print the commands that would be executed, but do not execute them')
  parser.add_argument(
    '--no-config',
    dest='no_config',
    action='store_true',
    help='Do not configure the started nodes')
  parser.add_argument(
    '-r','--reload-config',
    dest='reload',
    action='store',
    help='Reload saved configurations from specified directory')
  parser.add_argument(
    dest='action', action='store',
    choices=['up','down','restart','pause','unpause'],
    help='Action to execute on the selected nodes')
  parser.add_argument(
    dest='node', action='store', nargs='+',
    help='Node(s) to act on (node names, groups, or globs; separate them with spaces or commas)')
  parser_lab_location(parser,instance=True,action='change nodes in')

  return parser.parse_args(args)

#
# A restarted container loses its configuration: deploy the initial configuration
# (or reload the saved one) on the nodes we've just started
#
def configure_nodes(args: argparse.Namespace, node_list: typing.List[str]) -> None:
  limit = ','.join(node_list)
  if args.reload:
    cmd = ['netlab','config','--reload',args.reload,'--limit',limit]
  else:
    cmd = ['netlab','initial','--no-message','--limit',limit]

  if not external_commands.run_command(external_commands.set_ansible_flags(cmd)):
    log.fatal(f'netlab {cmd[1]} failed on nodes {limit}, aborting...','netlab node')

def run(cli_args: typing.List[str]) -> None:
  args = node_parse(cli_args)
  log.set_logging_flags(args)
  set_dry_run(args)

  if args.reload and args.no_config:
    log.fatal('Cannot combine --reload-config and --no-config')

  topology = load_snapshot(args,ghosts=False)
  args.limit = ','.join(args.node)
  node_list = _nodeset.from_args(args,topology)
  log.exit_on_error()

  for node in node_list:
    status = execute_node('control_node',node=topology.nodes[node],topology=topology,action=args.action)
    if status is None:
      log.error(f'The virtualization provider of node {node} does not support "netlab node"',module='node',skip_header=True)
    elif not status:
      log.error(f'Failed to {args.action} node {node}',module='node',skip_header=True)

  log.exit_on_error()

  if args.action in ('up','restart') and not args.no_config:
    configure_nodes(args,node_list)
