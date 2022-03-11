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

from . import common_parse_args, topology_parse_args, load_topology, load_snapshot_or_topology, external_commands,fs_cleanup
from .. import read_topology,augment,common
from .. import providers

#
# CLI parser for create-topology script
#
def down_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ topology_parse_args() ],
    prog="netlab down",
    description='Destroy the virtual lab')

  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default = 0,
    help='Verbose logging (where applicable)')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Remove all configuration files created by netlab create')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    default='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    dest='topology', action='store', nargs='?',
    help='Topology file (default: topology.yml)')

  return parser.parse_args(args)

def down_cleanup(topology: Box, verbose: bool = False) -> None:
  cleanup_list = topology.defaults.providers[topology.provider].cleanup or []
  cleanup_list.extend(topology.defaults.automation.ansible.cleanup)
  cleanup_list.append('netlab.snapshot.yml')
  fs_cleanup(cleanup_list,verbose)

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  topology = load_snapshot_or_topology(args)

  if args.topology:
    print(f"Reading lab topology from {args.topology}")
  else:
    print(f"Reading transformed lab topology from snapshot file {args.snapshot}")

  if topology is None:
    common.fatal('... could not read the lab topology, aborting')
    return

  settings = topology.defaults
  external_commands.run_probes(settings,topology.provider,1)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])

  if hasattr(provider,'pre_stop_lab') and callable(provider.pre_stop_lab):
    provider.pre_stop_lab(topology)

  external_commands.stop_lab(settings,topology.provider,2,"netlab down")

  if hasattr(provider,'post_stop_lab') and callable(provider.post_stop_lab):
    provider.post_stop_lab(topology)

  if args.cleanup:
    external_commands.print_step(3,"Cleanup configuration files",spacing = True)
    down_cleanup(topology,True)
