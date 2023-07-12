#
# netlab connect command
#
# Connect to a lab device using SSH or Docker
#
import typing
import os
import sys
import argparse
import subprocess
from enum import IntEnum

class LogLevel(IntEnum):
  NONE = 0
  INFO = 1
  ARGS = 2
  DRY_RUN = 3

from box import Box

from . import external_commands, set_dry_run

from . import load_snapshot
from ..outputs import common as outputs_common
from .. import common
from ..utils import strings

#
# CLI parser for 'netlab initial' command
#
def connect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab connect",
    description='Connect to a network device or an external tool',
    epilog='The rest of the arguments are passed to SSH or docker exec command')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    '-q','--quiet',
    dest='quiet',
    action='store_true',
    help='No logging')
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help='Print the commands that would be executed, but do not execute them')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    dest='host', action='store',
    help='Device or tool to connect to')

  return parser.parse_known_args(args)

def docker_connect(data: Box, rest: typing.List[str], log_level: LogLevel = LogLevel.INFO) -> None:
  host = data.ansible_host or data.host

  shell = data.get('docker_shell','bash -il')
  if not isinstance(shell,list):
    shell = str(shell).split(' ')

  args = ['docker','exec','-it',host] + shell
  if rest:
    args.extend(['-c',' '.join(rest)])

  if log_level == LogLevel.DRY_RUN:
    print(f"DRY RUN: {args}")
    return

  if log_level == LogLevel.ARGS:
    print("Executing: %s" % args)
  elif log_level == LogLevel.NONE:
    pass
  elif rest:
    sys.stderr.write(f"Connecting to container {host}, executing {' '.join(rest)}\n")
  else:
    sys.stderr.write(f"Connecting to container {host}, starting bash\n")
  sys.stdout.flush()
  sys.stderr.flush()

  subprocess.run(args)

def ssh_connect(data: Box, rest: typing.List[str], log_level: LogLevel = LogLevel.INFO) -> None:
  host = data.ansible_host or data.host
  args = ['ssh','-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-o','LogLevel ERROR']

  if data.ansible_ssh_pass:
    args = ['sshpass','-p',data.ansible_ssh_pass ] + args

  if data.ansible_port:
    args.extend(['-p',str(data.ansible_port)])

  if data.ansible_user:
    args.extend([data.ansible_user+"@"+host])
  else:
    args.extend([host])

  args.extend(rest)
  if log_level == LogLevel.DRY_RUN:
    print(f"DRY RUN: {args}")
    return

  if log_level == LogLevel.ARGS:
    print("Executing: %s" % args)
  elif log_level == LogLevel.NONE:
    pass
  else:
    sys.stderr.write(f"Connecting to {host} using SSH port {data.ansible_port or 22}\n")
    sys.stderr.flush()

  subprocess.run(args)

def connect_to_node(node: str, rest: list, topology: Box, log_level: LogLevel = LogLevel.INFO) -> None:
  host_data = outputs_common.adjust_inventory_host(
                node=topology.nodes[node],
                defaults=topology.defaults,
                group_vars=True)
  host_data.host = node
  connection = host_data.netlab_console_connection or host_data.ansible_connection

  if connection == 'docker':
    docker_connect(host_data,rest,log_level)
  elif connection in ['paramiko','ssh','network_cli','netconf','httpapi'] or not connection:
    if connection in ['netconf','httpapi']:
      print(f"Using SSH to connect to a device configured with {connection} connection")
    ssh_connect(host_data,rest,log_level)
  else:
    common.fatal(f'Unknown connection method {connection} for host {node}',module='connect')

def connect_to_tool(tool: str, rest: list, topology: Box, log_level: LogLevel = LogLevel.INFO) -> None:
  cmds = external_commands.get_tool_command(tool,'connect',topology,verbose=False)
  if cmds is None:
    msg = external_commands.get_tool_message(tool,topology)
    if not msg:
      common.fatal(f'Cannot connect to {tool}: the tool has no "connect" command',module='connect')
    else:
      print(msg)
    return

  for cmd in cmds:
    cmd = strings.eval_format(cmd,topology)
    exec_arg = [ 'bash', '-c', cmd ]
    if log_level == LogLevel.DRY_RUN:
      print(f"DRY RUN: {cmd}")
      continue
    if log_level == LogLevel.ARGS:
      print(f"Executing: {exec_arg}")
    elif log_level == LogLevel.INFO:
      print(f"Connecting to {tool}...")
    subprocess.run(exec_arg)

def get_log_level(args: argparse.Namespace) -> LogLevel:
  if args.dry_run:
    return LogLevel.DRY_RUN
  elif args.quiet:
    return LogLevel.NONE
  elif args.verbose:
    return LogLevel.ARGS
  else:
    return LogLevel.INFO

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = connect_parse(cli_args)
  log_level = get_log_level(args)
  set_dry_run(args)

  rest = [ f'"{arg}"' if " " in arg else arg for arg in rest ]      # Quote arguments with whitespaces

  topology = load_snapshot(args)
  host = args.host
  if host in topology.nodes:
    connect_to_node(host,rest,topology,log_level)
  elif host in topology.tools:
    connect_to_tool(host,rest,topology,log_level)
  else:
    common.fatal(f'Unknown host or external tool {host}')
