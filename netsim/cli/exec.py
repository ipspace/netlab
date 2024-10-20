#
# netlab exec command
#
# run a command on one or more lab devices
#
import typing
import os
import sys
import argparse
import subprocess
from enum import IntEnum

from box import Box

from . import external_commands, set_dry_run
from . import load_snapshot, _nodeset, parser_add_verbose
from .connect import quote_list, docker_connect, ssh_connect, connect_to_node,\
  LogLevel, get_log_level

from ..outputs import common as outputs_common
from ..utils import strings, log
from ..augment.groups import group_members

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
      '--snapshot',
      dest='snapshot',
      action='store',
      nargs='?',
      default='netlab.snapshot.yml',
      const='netlab.snapshot.yml',
      help='Transformed topology snapshot file')
  parser.add_argument(
      dest='node', action='store',
      help='Node(s) to run command on')
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
  selector = args.node
  args = argparse.Namespace(show=None,verbose=False, quiet=True,Output=True) 
  if selector in topology.nodes:
    connect_to_node(node=selector,args=args,rest=rest,topology=topology,log_level=log_level)
  elif selector in topology.groups:
    node_list = group_members(topology,selector)
    for node in node_list:           
        connect_to_node(node=node,args=args,rest=rest,topology=topology,log_level=log_level)   
  else:  
    node_list = _nodeset.parse_nodeset(selector,topology)
    for node in node_list:
        connect_to_node(node=node,args=args,rest=rest,topology=topology,log_level=log_level)
  
 

    


