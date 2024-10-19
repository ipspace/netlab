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
from ..outputs import common as outputs_common
from ..utils import strings, log

from .connect import quote_list, docker_connect, ssh_connect


class LogLevel(IntEnum):
  NONE = 0
  INFO = 1
  ARGS = 2
  DRY_RUN = 3


#
# CLI parser for 'netlab ' command
#
def connect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
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


def get_log_level(args: argparse.Namespace) -> LogLevel:
    if args.dry_run:
        return LogLevel.DRY_RUN
    elif args.quiet:
        return LogLevel.NONE
    elif args.verbose:
        return LogLevel.ARGS
    else:
        return LogLevel.INFO
       
def exec_on_node(
      args: argparse.Namespace,
      rest: list,
      topology: Box,
      node: str,
      log_level: LogLevel = LogLevel.INFO) -> typing.Union[bool,int,str]:
  
  host_data = outputs_common.adjust_inventory_host(
                node=topology.nodes[node],
                defaults=topology.defaults,
                group_vars=True)
  host_data.host = node
  connection = host_data.netlab_console_connection or host_data.ansible_connection

  if connection == 'docker':
    return docker_connect(host_data,args,rest,log_level)
  elif connection in ['paramiko','ssh','network_cli','netconf','httpapi'] or not connection:
    if connection in ['netconf','httpapi']:
      print(f"Using SSH to connect to a device configured with {connection} connection")
    return ssh_connect(host_data,args,rest,log_level)
  else:
    log.fatal(f'Unknown connection method {connection} for host {node}',module='connect')


def run(cli_args: typing.List[str]) -> None:
  (args, rest) = connect_parse(cli_args)
  log.set_logging_flags(args)
  log_level = get_log_level(args)
  set_dry_run(args)

  if not rest:
    log.fatal("No command to execute on node(s) was specified. Aborting.")

  rest = quote_list(rest)    
  topology = load_snapshot(args)
  selector = args.node

  if selector in topology.nodes:
    exec_on_node(args,rest,topology,selector,log_level)
  elif selector in topology.groups:
    node_list= topology.groups.get(selector, {}).get('members', [])
    for node in node_list:
        exec_on_node(args,rest,topology,node,log_level)   
  else:  
    node_list = _nodeset.parse_nodeset(selector,topology)
    for node in node_list:
        exec_on_node(args,rest,topology,node,log_level)
  
 

    


