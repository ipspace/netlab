#
# netlab consolidate command
#
# Consolidates all YAML files into a single JSON file for faster loading
#
import argparse
import typing
from pathlib import Path

from box import Box

from ..utils import consolidate, log
from . import common_parse_args, error_and_exit, topology_parse_args

def consolidate_parse(args: typing.List[str]) -> argparse.Namespace:
  """Parse arguments for consolidate command"""
  parents = [common_parse_args(True), topology_parse_args()]
  parser = argparse.ArgumentParser(
    parents=parents,
    prog='netlab consolidate',
    description='Consolidate all YAML files into a single JSON file for faster loading')

  parser.add_argument(
    'topology',
    nargs='?',
    action='store',
    default=None,
    help='Topology file to consolidate (optional: if omitted, consolidates all system/package YAML files)')

  parser.add_argument(
    '-o', '--output',
    dest='output',
    action='store',
    default='netlab.consolidated.json',
    help='Output JSON file (default: netlab.consolidated.json)')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  """Run the consolidate command"""
  args = consolidate_parse(cli_args)

  try:
    if args.topology:
      # Consolidate specific topology file
      topology_file = args.topology
      if not Path(topology_file).exists():
        error_and_exit(f'Topology file {topology_file} does not exist', module='consolidate')

      # Get defaults lists if specified
      user_defaults = None
      system_defaults = None

      # Build defaults list similar to load function
      from ..utils import read as _read
      temp_topology = Box()
      defaults_list = _read.build_defaults_list(
        temp_topology,
        user_defaults=user_defaults,
        system_defaults=system_defaults
      )

      consolidate.consolidate_to_json(
        topology_file=topology_file,
        output_file=args.output,
        user_defaults=defaults_list if user_defaults is None else user_defaults,
        system_defaults=defaults_list if system_defaults is None else system_defaults
      )
      log.status_green('CONSOLIDATED', '')
      print(f'All YAML files consolidated into {args.output}')
      print(f'Use --json-cache {args.output} with netlab create to use this cache')
    else:
      # Consolidate all system/package YAML files
      consolidate.consolidate_all_system_files(output_file=args.output)
      log.status_green('CONSOLIDATED', '')
      print(f'All system/package YAML files consolidated into {args.output}')
      print(f'Use --json-cache {args.output} with netlab create to use this cache')
  except Exception as ex:
    error_and_exit(f'Error consolidating files: {ex}', module='consolidate')

