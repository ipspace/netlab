#
# netlab capture command
#
# Starts packet capturing on specified node/interface
#
import sys
import typing
import argparse

from . import load_snapshot,_nodeset,external_commands
from .. import providers
from ..augment import devices
from ..utils import strings,log

#
# CLI parser for 'netlab capture' command
#
def capture_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab capture",
    description='Start a packet capture on the specified node/interface')
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
    help='Node on which you want to capture traffic')
  parser.add_argument(
    dest='intf', action='store',
    help='Interface on which you want to capture traffic')
  parser.add_argument(
    '--command',
    dest='command',
    action='store',
    nargs='?',
    default='tcpdump -i {intf}',
    const='tcpdump -i {intf}',
    help='Command to use for packet capture')

  return parser.parse_known_args(args)

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = capture_parse(cli_args)

  topology = load_snapshot(args)

  if args.node and args.node not in topology.nodes:
    log.error(
      f'Unknown node {args.node}',
      category=log.FatalError,
      module='capture',
      skip_header=True,
      exit_on_error=True,
      more_hints=[ 'Use "netlab status" to display the node names in the current lab topology' ])
  
  ndata = topology.nodes[args.node]
  if args.intf and args.intf not in [ intf.ifname for intf in ndata.interfaces ]:
    log.error(
      f'Invalid interface name {args.intf} for node {args.node} (device {ndata.device})',
      category=log.FatalError,
      module='capture',
      skip_header=True,
      exit_on_error=True,
      more_hints=[ f'Use "netlab report --node {args.node} addressing" to display valid interface names and their descriptions' ])
    sys.exit(1)

  node_provider = devices.get_provider(ndata,topology.defaults)
  p_module = providers.get_provider_module(topology,node_provider)
  p_cmd = p_module.call('capture_command',ndata,topology,args)

  if p_cmd is None:
    log.error(
      f'Cannot perform packet capture for node {args.node} using provider {node_provider}',
      category=log.FatalError,
      exit_on_error=True,
      skip_header=True)

  p_cmd_list = p_cmd.split(' ')
  if not rest and 'tcpdump' in args.command:
    rest = [ '-l', '-v' ]

  p_cmd_list.extend(rest)
  print(f'Starting packet capture on {args.node}/{args.intf}: {" ".join(p_cmd_list)}')
  external_commands.run_command(p_cmd_list)
