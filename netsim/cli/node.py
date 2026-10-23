#
# netlab node command
#
# Start, stop, restart, pause, or unpause individual lab nodes without touching the rest of the lab
#
import argparse
import typing

from ..providers import execute_node
from ..utils import log
from . import _nodeset, load_snapshot, parser_add_verbose, parser_lab_location, set_dry_run


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
    dest='node', action='store',
    help='Node(s) to act on (node names, groups, or globs, separated by commas)')
  parser.add_argument(
    dest='action', action='store',
    choices=['up','down','restart','pause','unpause'],
    help='Action to execute on the selected nodes')
  parser_lab_location(parser,instance=True,action='change nodes in')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = node_parse(cli_args)
  log.set_logging_flags(args)
  set_dry_run(args)

  topology = load_snapshot(args,ghosts=False)
  node_list = _nodeset.parse_nodeset(args.node,topology)
  log.exit_on_error()

  for node in node_list:
    status = execute_node('control_node',node=topology.nodes[node],topology=topology,action=args.action)
    if status is None:
      log.error(f'The virtualization provider of node {node} does not support "netlab node"',module='node',skip_header=True)
    elif not status:
      log.error(f'Failed to {args.action} node {node}',module='node',skip_header=True)

  log.exit_on_error()
