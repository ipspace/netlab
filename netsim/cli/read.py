#
# netlab read command
#
# Read network topology, add default settings, and dump the results
#
import typing
import sys
import argparse

from . import common_parse_args, topology_parse_args, parser_add_debug
from .. import augment
from ..utils import log, strings, read as _read
from ..augment.main import transform_setup

#
# CLI parser for 'netlab read' command
#
def read_topology_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(),topology_parse_args() ],
    prog="netlab read",
    description='Read network topology, add default settings, and dump the results')

  parser.add_argument(dest='topology', action='store', help='Topology file')
  parser.add_argument(
    '-o','--output',
    dest='output',
    type=argparse.FileType('w'),
    default=sys.stdout,
    action='store',
    help='Output file')
  
  parser_add_debug(parser)
  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = read_topology_parse(cli_args)
  log.set_logging_flags(args)
  topology = _read.load(args.topology,args.defaults)

  if 'settings' in args:
    topology.nodes = augment.nodes.create_node_dict(topology.nodes)
    _read.add_cli_args(topology,args)

  log.exit_on_error()

  transform_setup(topology)
  args.output.write(strings.get_yaml_string(topology))
