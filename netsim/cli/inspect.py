#
# netlab inspect command
#
# Inspect data structures in transformed lab topology
#
import typing
import os
import sys
import argparse

from box import Box,BoxList

from . import load_snapshot,_nodeset
from ..outputs import _TopologyOutput
from ..outputs import common as outputs_common
from ..utils import strings,log
from ..data.types import must_be_id
from ..data import global_vars

#
# CLI parser for 'netlab inspect' command
#
def inspect_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in transformed lab topology')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    '--node',
    dest='node', action='store',
    help='Display data for selected node(s)')
  parser.add_argument(
    '--format',
    dest='format', action='store',
    default='yaml',
    choices=['yaml','json'],
    help='Select data presentation format')
  parser.add_argument(
    dest='expr', action='store',
    nargs='?',
    help='Data selection expression')

  return parser.parse_args(args)

def inspect_value(topology: Box, args: argparse.Namespace) -> None:
  o_module = args.format or 'yaml'
  o_param  = f'{o_module}:{args.expr or "."}'
  inspect_module = _TopologyOutput.load(o_param,topology.get('defaults.outputs.{o_module}',{}))
  if not inspect_module:
    log.fatal(f'Cannot load the data inspection output module {o_module}, aborting')

  inspect_module.write(topology)

def fmt_value(v: typing.Union[Box,BoxList], fmt: str) -> str:
  value = v.to_yaml() if fmt == 'yaml' else v.to_json()
  return value.strip('\n')

def inspect_node(topology: Box, node_list: list, args: argparse.Namespace) -> None:
  o_format = args.format or 'yaml'
  hdr_row: list = []
  data_row: list = []

  for node in node_list:
    node_data = outputs_common.adjust_inventory_host(
                  node=topology.nodes[node],
                  defaults=topology.defaults,
                  group_vars=True)
    if len(node_list) == 1:
      inspect_value(node_data,args)
      return
    else:
      select = node_data.get(args.expr,None) if args.expr else node_data
      value  = fmt_value(select,o_format) if isinstance(select,Box) or isinstance(select,BoxList) else str(select)
      hdr_row.append(node)
      data_row.append(value)

  strings.print_table(hdr_row,[ data_row ])

def run(cli_args: typing.List[str]) -> None:
  args = inspect_parse(cli_args)
  topology = load_snapshot(args)
  log.init_log_system(False)

  if args.node:
    node_list = _nodeset.parse_nodeset(args.node,topology)
    inspect_node(topology,node_list,args)
  else:
    inspect_value(topology,args)
