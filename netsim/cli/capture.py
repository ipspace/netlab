#
# netlab capture command
#
# Starts packet capturing on specified node/interface
#
import argparse
import typing

from .. import providers
from ..augment import devices
from ..utils import log, strings
from . import error_and_exit, external_commands, load_snapshot, parser_lab_location


#
# CLI parser for 'netlab capture' command
#
def capture_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab capture",
    description='Start a packet capture on the specified node/interface',
    epilog='All other arguments are passed directly to the packet-capturing utility')
  parser.add_argument(
    dest='node', action='store',
    help='Node on which you want to capture traffic')
  parser.add_argument(
    dest='intf', action='store',
    nargs='?',
    help='Interface on which you want to capture traffic')
  parser_lab_location(parser,instance=True,action='capture traffic in')

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
  if ndata.get('unmanaged',False):
    error_and_exit(f'Node {args.node} is an unmanaged node and cannot be used in the capture command')
  intf_hint = [ f'Use "netlab report --node {args.node} addressing" to display valid interface names and their descriptions' ]
  if not args.intf:
    error_and_exit('Missing interface name',more_hints=intf_hint)

  # Try to find the capture interface based on the device interface name
  intf_list = [ intf for intf in ndata.interfaces if intf.ifname == args.intf ]

  # Not found, try to find it based on the clab interface name (used for vrnetlab containers)
  if not intf_list:
    intf_list = [ intf for intf in ndata.interfaces if intf.clab.name == args.intf ]

  # Still an empty list of matches, obviously the interface name is incorrect
  if not intf_list:
    error_and_exit(
      f'Invalid interface name {args.intf} for node {args.node} (device {ndata.device})',
      more_hints=intf_hint)

  intf = intf_list[0]                             # Now get the interface data of the first (and hopefully only) match
  if intf.get('clab.name',None):                  # ... and if we have clab interface name (vrnetlab container)
    args.intf = intf.clab.name                    # ... change the capture interface name

  node_provider = devices.get_provider(ndata,topology.defaults)
  p_module = providers.get_provider_module(topology,node_provider)
  p_cmd = p_module.call('capture_command',ndata,topology,args)

  if p_cmd is None:
    log.error(
      f'Cannot perform packet capture for node {args.node} using provider {node_provider}',
      module='capture',
      category=log.FatalError,
      exit_on_error=True,
      skip_header=True)

  if not [ flag for flag in rest if flag.startswith('-') ]:
    rest = strings.string_to_list(topology.defaults.netlab.capture.command_args) + rest

  p_cmd += rest
  print(f'Starting packet capture on {args.node}/{args.intf}: {" ".join(p_cmd)}')
  status = external_commands.run_command(p_cmd,ignore_errors=True,return_exitcode=True)
  if status == 1:
    log.error(
      f'Packet capturing utility reported an error',
      category=log.FatalError,
      module='capture',
      skip_header=True,
      exit_on_error=True)
