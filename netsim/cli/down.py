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

from . import common_parse_args, topology_parse_args, load_topology, external_commands
from .. import read_topology,augment,common
from .. import providers

#
# CLI parser for create-topology script
#
def down_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(True),topology_parse_args() ],
    prog="netlab down",
    description='Destroy the virtual lab')

  parser.add_argument(
    dest='topology', action='store', nargs='?',
    type=argparse.FileType('r'),
    default='topology.yml',
    help='Topology file (default: topology.yml)')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  topology = load_topology(args)

  augment.main.transform(topology)
  common.exit_on_error()

  settings = topology.defaults
  external_commands.run_probes(settings,topology.provider,1)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])

  if hasattr(provider,'pre_stop_lab') and callable(provider.pre_stop_lab):
    provider.pre_stop_lab(topology)

  external_commands.stop_lab(settings,topology.provider,2,"netlab down")

  if hasattr(provider,'post_stop_lab') and callable(provider.post_stop_lab):
    provider.post_stop_lab(topology)
