#
# netlab tc command
#
# Configure/enable/disable link impairment and traffic control
#
import argparse
import typing

from box import Box

from ..data import get_empty_box
from ..providers import execute_node
from ..utils import log
from . import (
  error_and_exit,
  load_snapshot,
  parser_add_verbose,
  parser_lab_location,
  parser_subcommands,
  subcommand_usage,
)


def tc_select_intf(args: argparse.Namespace, topology: Box, all: bool = False, need_intf: bool = False) -> list:
  intf_list = []
  ifname = args.intf if 'intf' in args else None
  if not ifname and need_intf:
    error_and_exit('You must specify a node and an interface')
  if ifname and not args.node:
    error_and_exit('If you want to specify an interface, you must also specify a node')
  if args.node and args.node not in topology.nodes:
    error_and_exit(f'Unknown node {args.node}, use "netlab status" to display node names')
  node_list = [ topology.nodes[args.node] ] if args.node else list(topology.nodes.values())

  for node in node_list:
    for intf in node.interfaces:
      if intf.ifname == ifname or all or (not ifname and 'tc' in intf):
        intf_list.append((node,intf))

  if not intf_list:
    if ifname:
      error_and_exit(
        f'Cannot find the specified interface {ifname} on node {args.node}',
        more_hints=f'Use "netlab report --node {args.node} addressing" to display valid interface names and their descriptions')
    else:
      error_and_exit(f'No interfaces {"on node "+args.node if args.node else ""} have tc parameters in lab topology')

  return intf_list

def tc_parser_node_intf(parser: argparse.ArgumentParser, action: str) -> None:
  parser.add_argument(
    '-n','--node',
    dest='node',
    action='store',
    help=f'{action} traffic control only on selected node')
  parser.add_argument(
    '-i','--interface',
    dest='intf',
    action='store',
    help=f'{action} traffic control only on selected interface')

def tc_enable_parser(parser: argparse.ArgumentParser) -> None:
  tc_parser_node_intf(parser,'Enable')
  return

def tc_enable(args: argparse.Namespace, topology: Box) -> None:
  tc_list = tc_select_intf(args,topology)
  for tc_entry in tc_list:
    (ndata,intf) = tc_entry
    execute_node('set_tc',node=ndata,topology=topology,intf=intf,error='intf' in args)

def tc_disable_parser(parser: argparse.ArgumentParser) -> None:
  tc_parser_node_intf(parser,'Disable')
  parser.add_argument(
    '--all',
    dest='all',
    action='store_true',
    help='Disable traffic control on all lab links')

def tc_disable(args: argparse.Namespace, topology: Box) -> None:
  tc_list = tc_select_intf(args,topology,all=bool(args.all))
  for tc_entry in tc_list:
    (ndata,intf) = tc_entry
    intf.tc = {}
    if log.VERBOSE:
      print(f'Disabling TC on node {ndata.name} interface {intf.ifname}')
    execute_node('set_tc',node=ndata,topology=topology,intf=intf,error='intf' in args)

def tc_show_parser(parser: argparse.ArgumentParser) -> None:
  tc_parser_node_intf(parser,'Display')
  return

def tc_show(args: argparse.Namespace, topology: Box) -> None:
  tc_list = tc_select_intf(args,topology)
  for tc_entry in tc_list:
    (ndata,intf) = tc_entry
    intf.tc = { 'action': 'show' }
    execute_node('set_tc',node=ndata,topology=topology,intf=intf,error='intf' in args)

def tc_set_parser(parser: argparse.ArgumentParser) -> None:
  tc_parser_node_intf(parser,'Change')
  parser.add_argument('--corrupt',dest='corrupt',action='store',help='Percentage of corrupt packets',type=float)
  parser.add_argument('--delay',dest='delay',action='store',help='Delay in msec',type=float)
  parser.add_argument('--duplicate',dest='duplicate',action='store',help='Percentage of duplicate packets',type=float)
  parser.add_argument('--jitter',dest='jitter',action='store',help='Jitter in msec',type=float)
  parser.add_argument('--loss',dest='loss',action='store',help='Percentage of lost packets',type=float)
  parser.add_argument('--rate',dest='rate',action='store',help='Rate in kbps',type=float)
  parser.add_argument('--reorder',dest='reorder',action='store',help='Percentage of reordered packets',type=float)
  parser.add_argument('--modify',dest='modify',action='store_true',help='Modify existing traffic control parameters')

def tc_set(args: argparse.Namespace, topology: Box) -> None:
  tc_data = get_empty_box()
  args_dict = vars(args)
  for kw in topology.defaults.attributes.link.tc.keys():
    if args_dict.get(kw,None):
      tc_data[kw] = args_dict[kw]
  if args.modify:
    tc_data.action = 'modify'

  if 'rate' in tc_data:
    tc_data.rate = 1000 * tc_data.rate

  tc_list = tc_select_intf(args,topology)
  for tc_entry in tc_list:
    (ndata,intf) = tc_entry
    intf.tc = tc_data
    execute_node('set_tc',node=ndata,topology=topology,intf=intf,error='intf' in args)

tc_dispatch: dict = {
  'enable': {
    'exec':  tc_enable,
    'parser': tc_enable_parser,
    'description': 'Enable topology-defined link impairments'
  },
  'disable': {
    'exec':  tc_disable,
    'parser': tc_disable_parser,
    'description': 'Disable link impairments'
  },
  'show': {
    'exec':  tc_show,
    'parser': tc_show_parser,
    'description': 'Display configured traffic control'
  },
  'set': {
    'exec':  tc_set,
    'parser': tc_set_parser,
    'description': 'Set or modify traffic control parameters'
  }
}

def tc_parse(args: typing.List[str]) -> argparse.Namespace:
  global tc_dispatch

  parser = argparse.ArgumentParser(
    prog="netlab tc",
    description='Link impairment and traffic control utilities',
    epilog="Use 'netlab tc subcommand -h' to get subcommand usage guidelines")
  parser_add_verbose(parser,quiet=True)
  parser_lab_location(parser,instance=True,i_used=True)
  parser_subcommands(parser,tc_dispatch)
  
  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  global tc_dispatch

  if not cli_args:
    subcommand_usage(tc_dispatch)
    return

  args = tc_parse(cli_args)
  log.set_logging_flags(args)
  topology = load_snapshot(args)
  args.execute(args,topology)
