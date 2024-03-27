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
from .external_commands import run_command

class LogLevel(IntEnum):
  NONE = 0
  INFO = 1
  ARGS = 2
  DRY_RUN = 3

from box import Box

from . import external_commands, set_dry_run

from . import load_snapshot, parser_add_verbose
from ..outputs import common as outputs_common
from ..utils import strings, log

#
# CLI parser for 'netlab initial' command
#
def connect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab connect",
    description='Connect to a network device or an external tool',
    epilog='The rest of the arguments are passed to SSH or docker exec command')
  parser_add_verbose(parser)
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
  parser.add_argument(
    '-s','--show',
    dest='show',
    action='store',
    nargs='+',
    help='Show command to execute on the device')

  return parser.parse_known_args(args)

def docker_connect(
      data: Box,
      p_args: argparse.Namespace,
      rest: typing.List[str],
      log_level: LogLevel = LogLevel.INFO) -> typing.Union[bool,str]:
  host = data.ansible_host or data.host

  shell = data.get('docker_shell','bash' if rest else 'bash -il')
  if not isinstance(shell,list):
    shell = str(shell).split(' ')

  c_args = ['docker','exec','-it',host] + shell
  if rest:
    c_args.extend(['-c',' '.join(rest)])

  if log_level == LogLevel.DRY_RUN:
    print(f"DRY RUN: {c_args}")
    return True

  if log_level == LogLevel.ARGS:
    print(f"Executing: {c_args}")
  elif log_level == LogLevel.NONE:
    pass
  elif rest:
    sys.stderr.write(f"Connecting to container {host}, executing {' '.join(rest)}\n")
  else:
    sys.stderr.write(f"Connecting to container {host}, starting bash\n")
  sys.stdout.flush()
  sys.stderr.flush()

  need_output = 'output' in p_args and p_args.output
  return run_command(c_args,check_result=need_output,return_stdout=need_output,ignore_errors=True)

def ssh_connect(
      data: Box,
      p_args: argparse.Namespace,
      rest: typing.List[str],
      log_level: LogLevel = LogLevel.INFO) -> typing.Union[bool,str]:
  host = data.ansible_host or data.host
  c_args = ['ssh','-o','UserKnownHostsFile=/dev/null','-o','StrictHostKeyChecking=no','-o','LogLevel=ERROR']

  if data.ansible_ssh_pass:
    c_args = ['sshpass','-p',data.ansible_ssh_pass ] + c_args

  if data.ansible_port:
    c_args.extend(['-p',str(data.ansible_port)])

  if data.ansible_user:
    c_args.extend([data.ansible_user+"@"+host])
  else:
    c_args.extend([host])

  c_args.extend(rest)
  if log_level == LogLevel.DRY_RUN:
    print(f"DRY RUN: {c_args}")
    return True

  if log_level != LogLevel.NONE:
    exec_args = ', executing ' + ' '.join(rest) if rest else ''
    sys.stderr.write(f"Connecting to {host} using SSH port {data.ansible_port or 22}{exec_args}\n")

  if p_args.verbose >= 2:
    sys.stderr.write(f'Executing: {c_args}\n')

  sys.stderr.flush()
  need_output = 'output' in p_args and p_args.output
  return run_command(c_args,check_result=need_output,return_stdout=need_output,ignore_errors=True)

def quote_list(args: list) -> list:
  return [ f'"{arg}"' if " " in arg else arg for arg in args ]

def create_show_command(host: Box, rest: list) -> list:
  got_args = False
  show_cmd = []
  for arg in host.netlab_show_command:
    if '$@' in arg:
      show_cmd.append(arg.replace('$@',' '.join(rest)))
      got_args = True
    else:
      show_cmd.append(arg)

  if not got_args:
    show_cmd.extend(rest)

  return show_cmd

def create_command_list(host: Box, args: argparse.Namespace, rest: list) -> list:
  if rest and args.show:
    log.fatal(
      'Cannot run a command and a show command at the same time.\n' +
      '... Make --show the first argument after the node name')

  if args.show:
    show_cmd = create_show_command(host,args.show)
    if host.netlab_show_command:
      return quote_list(show_cmd)
    else:
      return [ 'show' ] + args.show
  else:
    return rest

def connect_to_node(
      args: argparse.Namespace,
      rest: list,
      topology: Box,
      log_level: LogLevel = LogLevel.INFO) -> typing.Union[bool,str]:
  node = args.host
  host_data = outputs_common.adjust_inventory_host(
                node=topology.nodes[node],
                defaults=topology.defaults,
                group_vars=True)
  host_data.host = node
  connection = host_data.netlab_console_connection or host_data.ansible_connection

  rest = create_command_list(host_data,args,rest)

  if connection == 'docker':
    return docker_connect(host_data,args,rest,log_level)
  elif connection in ['paramiko','ssh','network_cli','netconf','httpapi'] or not connection:
    if connection in ['netconf','httpapi']:
      print(f"Using SSH to connect to a device configured with {connection} connection")
    return ssh_connect(host_data,args,rest,log_level)
  else:
    log.fatal(f'Unknown connection method {connection} for host {node}',module='connect')

def connect_to_tool(tool: str, rest: list, topology: Box, log_level: LogLevel = LogLevel.INFO) -> None:
  cmds = external_commands.get_tool_command(tool,'connect',topology,verbose=False)
  if cmds is None:
    msg = external_commands.get_tool_message(tool,topology)
    if not msg:
      log.fatal(f'Cannot connect to {tool}: the tool has no "connect" command',module='connect')
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

  rest = quote_list(rest)     # Quote arguments with whitespaces
  topology = load_snapshot(args)
  host = args.host

  if host in topology.nodes:
    connect_to_node(args,rest,topology,log_level)
  elif host in topology.tools:
    connect_to_tool(host,rest,topology,log_level)
  else:
    log.fatal(f'Unknown host or external tool {host}')
