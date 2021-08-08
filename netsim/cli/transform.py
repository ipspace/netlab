#
# netlab transform command
#
# Read network topology, do the data model transformation, and output the result in YAML format
#
import typing
import sys
import argparse

from . import common_parse_args, topology_parse_args
from .. import set_logging_flags
from .. import read_topology
from .. import common
from .. import augment
from ..augment.topology import cleanup_topology

#
# CLI parser for 'netlab read' command
#
def transform_topology_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(),topology_parse_args() ],
    prog="netlab read",
    description='Read network topology, do the data model transformation, and dump the results')

  parser.add_argument(
    dest='topology',
    type=argparse.FileType('r'),
    action='store',
    help='Topology file')
  parser.add_argument(
    '-o','--output',
    dest='output',
    type=argparse.FileType('w'),
    default=sys.stdout,
    action='store',
    help='Output file')
  parser.add_argument(
    '-f','--format',
    dest='format',
    default='yaml',
    choices=['yaml', 'json'],
    action='store',
    help='Output format')
  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = transform_topology_parse(cli_args)
  set_logging_flags(args)
  topology = read_topology.load(args.topology.name,args.defaults,"package:topology-defaults.yml")
  read_topology.add_cli_args(topology,args)
  common.exit_on_error()

  augment.main.transform(topology)
  topology = cleanup_topology(topology)
  if args.format == 'yaml':
    args.output.write(topology.to_yaml())
  elif args.format == 'json':
    args.output.write(topology.to_json(indent=2))
  else:
    common.fatal('Invalid output format: %s' % args.format,'transform')
