#
# netlab read command
#
# Read network topology, add default settings, and dump the results
#
import typing
import sys
import argparse

from . import common_parse_args, topology_parse_args
from .. import set_logging_flags
from .. import read_topology,common
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
  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = read_topology_parse(cli_args)
  set_logging_flags(args)
  topology = read_topology.load(args.topology,args.defaults,"package:topology-defaults.yml")
  read_topology.add_cli_args(topology,args)
  common.exit_on_error()

  transform_setup(topology)
  args.output.write(topology.to_yaml())
