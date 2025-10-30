#
# netlab inspect command
#
# Inspect data structures in transformed lab topology
#
import argparse
import typing

from box import Box, BoxList

from ..data import get_empty_box
from ..outputs import _TopologyOutput
from ..outputs import common as outputs_common
from ..utils import log, strings
from . import _nodeset, load_data_source, parser_add_verbose, parser_data_source


#
# CLI parser for 'netlab inspect' command
#
def inspect_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in a lab topology')
  parser.add_argument(
    '--node',
    dest='node', action='store',
    help='Display data for selected node(s)')
  parser.add_argument(
    '--all',
    dest='all', action='store_true',
    help='Add global Ansible variables to node data')
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
  parser_add_verbose(parser,verbose=False)
  parser_data_source(parser,action='inspect')

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

"""
Read Ansible variables for the 'all' group (paths, pools, prefixes)
"""
def read_all_group_vars() -> Box:
  try:
    return Box().from_yaml(filename='group_vars/all/topology.yml')
  except Exception as ex:
    log.fatal(f"Cannot read variables for 'all' group: {str(ex)}")    

def inspect_node(topology: Box, node_list: list, args: argparse.Namespace) -> None:
  o_format = args.format or 'yaml'
  hdr_row: list = []
  data_row: list = []

  global_data = read_all_group_vars() if args.all else get_empty_box()
    
  for node in node_list:
    node_data = outputs_common.adjust_inventory_host(
                  node=topology.nodes[node],
                  defaults=topology.defaults,
                  group_vars=True)
    if global_data:
      node_data = global_data + node_data
    if len(node_list) == 1:
      inspect_value(node_data,args)
      return
    else:
      select = node_data.get(args.expr,None) if args.expr else node_data
      value  = fmt_value(select,o_format) if isinstance(select,Box) or isinstance(select,BoxList) else str(select)
      hdr_row.append(node)
      data_row.append(value)

  strings.print_table(hdr_row,[ data_row ],markup=False)    # Print the resulting table, disabling Rich markup in cells

def run(cli_args: typing.List[str]) -> None:
  args = inspect_parse(cli_args)
  topology = load_data_source(args)
  log.init_log_system(False)

  if args.node:
    node_list = _nodeset.parse_nodeset(args.node,topology)
    inspect_node(topology,node_list,args)
  else:
    inspect_value(topology,args)
