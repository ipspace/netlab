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

from box import Box

from . import ansible
from . import common_parse_args
from .. import common

#
# CLI parser for 'netlab initial' command
#
def connect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab connect",
    description='Connect to a network device',
    epilog='The rest of the arguments are passed to SSH or docker exec command')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    dest='host', action='store',
    help='Device to connect to')

  return parser.parse_known_args(args)

def get_inventory_data(host: str) -> typing.Optional[dict]:
  return ansible.inventory(host)

def docker_connect(data: Box, rest: typing.List[str], verbose: bool = False) -> None:
  host = data.ansible_host or data.host
  args = ['docker','exec','-it',host,'bash','-il']
  if rest:
    sys.stderr.write("Connecting to container %s, executing %s\n" % (host," ".join(rest)))
    args.extend(['-c','"'+' '.join(rest)+'"'])
  else:
    sys.stderr.write("Connecting to container %s, starting bash\n" % host)
  sys.stderr.flush()
  subprocess.run(args)

def ssh_connect(data: Box, rest: typing.List[str], verbose: bool = False) -> None:
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
  if verbose:
    print("Executing: %s" % args)
  else:
    sys.stderr.write("Connecting to %s using SSH port %s\n" % (host,data.ansible_port or 22))
    sys.stderr.flush()

  subprocess.run(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = connect_parse(cli_args)

  host_data = Box(get_inventory_data(args.host),box_dots=True,default_box=True)
  host_data.host = args.host
  connection = host_data.ansible_connection

  if connection == 'docker':
    docker_connect(host_data,rest,args.verbose)
  elif connection in ['paramiko','ssh','network_cli'] or not connection:
    ssh_connect(host_data,rest,args.verbose)
  else:
    common.fatal('Unknown connection method %s for host %s' % (connection,args.host),'connect')
