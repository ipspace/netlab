#
# netlab create command
#
# Creates virtualization provider configuration and automation inventory from
# the specified topology
#
import argparse
import typing
import textwrap
from box import Box

from . import common_parse_args
from . import external_commands
from .. import read_topology,augment,common

#
# CLI parser for create-topology script
#
def down_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(True) ],
    prog="netlab down",
    description='Destroy the virtual lab')

  parser.add_argument(
    '--defaults', dest='defaults', action='store',
    default='topology-defaults.yml',
    help='Local topology defaults file')
  parser.add_argument(
    dest='topology', action='store', nargs='?',
    type=argparse.FileType('r'),
    default='topology.yml',
    help='Topology file (default: topology.yml)')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  common.set_logging_flags(args)
  topology = read_topology.load(args.topology.name,args.defaults,"package:topology-defaults.yml")
  common.exit_on_error()

  augment.main.transform(topology)
  common.exit_on_error()

  settings = topology.defaults
  external_commands.run_probes(settings,topology.provider)
  external_commands.stop_lab(settings,topology.provider,1)
