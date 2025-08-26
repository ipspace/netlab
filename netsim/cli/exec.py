#
# netlab exec command
#
# run a command on one or more lab devices
#
import argparse
import typing

from ..utils import log
from . import _nodeset, load_snapshot, parser_add_verbose, parser_lab_location, set_dry_run
from .connect import LogLevel, connect_to_node, get_log_level, quote_list


#
# CLI parser for 'netlab ' command
#
def exec_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
      prog="netlab exec",
      description='Run a command on one or more network devices',
      epilog='The rest of the arguments are passed to SSH or docker exec command')
  parser_add_verbose(parser)
  parser.add_argument(
      '--dry-run',
      dest='dry_run',
      action='store_true',
      help='Print the hosts and the commands that would be executed on them, but do not execute them')
  parser.add_argument(
      '--header',
      dest='header',
      action='store_true',
      help='Add node headers before command printouts')
  parser.add_argument(
      dest='node', action='store',
      help='Node(s) to run command on')
  parser_lab_location(parser,instance=True,action='execute commands in')

  return parser.parse_known_args(args)
      
def run(cli_args: typing.List[str]) -> None:
  (args, rest) = exec_parse(cli_args)
  log.set_logging_flags(args)
  log_level = get_log_level(args)
  set_dry_run(args)

  if not rest:
    log.fatal("No command to execute on node(s) was specified. Aborting.")

  rest = quote_list(rest)    
  topology = load_snapshot(args)
  node_list = _nodeset.parse_nodeset(args.node,topology)
  p_header = args.header

  args = argparse.Namespace(show=None,verbose=False,quiet=True,Output=True)
  for node in node_list:
    if p_header:
      print('=' * 80)
      print(f'{node}: executing {" ".join(rest)}')
      print('=' * 80)
    connect_to_node(
      node=node,
      args=args,
      rest=rest,
      topology=topology,
      log_level=LogLevel.NONE if p_header else log_level)
