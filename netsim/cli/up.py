#
# netlab up command
#
# * Transform lab topology and create provider and automation files,
#   or read transformed lab topology from snapshot file
# * Start the lab, including provider-specific pre- and post-start hooks
#
import typing
import argparse
import os
import glob
import subprocess
import shutil

from box import Box
from pathlib import Path

from .. import common
from . import create
from . import external_commands
from . import common_parse_args, load_snapshot_or_topology, get_message
from .. import providers
from .. import read_topology

#
# Extra arguments for 'netlab up' command
#
def up_parse_args(standalone: bool) -> argparse.ArgumentParser:
  parse_parents = [ common_parse_args() ] if standalone else []
  parser = argparse.ArgumentParser(
    description='netlab up extra arguments',
    parents = parse_parents,
    add_help=standalone)
  parser.add_argument(
    '--no-config',
    dest='no_config',
    action='store_true',
    help='Do not configure lab devices')
  parser.add_argument(
    '--fast-config',
    dest='fast_config',
    action='store_true',
    help='Use fast device configuration (Ansible strategy = free)')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    const='netlab.snapshot.yml',
    help='Use netlab snapshot file created by a previous lab run')
  return parser

def run(cli_args: typing.List[str]) -> None:
  up_args_parser = up_parse_args(False)                       # Try to parse the up-specific arguments
  (args,rest) = up_args_parser.parse_known_args(cli_args)

  if args.snapshot:                                           # If we're using the snapshot file...
    up_args_parser = up_parse_args(True)                      # ... create a stricter parser with help option
    args = up_args_parser.parse_args(cli_args)                # ... and reparse
    common.set_logging_flags(args)                            # ... use these arguments to set logging flags and read the snapshot

    topology = read_topology.read_yaml(filename=args.snapshot)
    if topology is None:
      common.fatal(f'Cannot read snapshot file {args.snapshot}, aborting...')
      return

    print(f"Using transformed lab topology from snapshot file {args.snapshot}")
  else:                                                       # No snapshot file, use 'netlab create' parser
    topology = create.run(cli_args,'up','Create configuration files, start a virtual lab, and configure it',up_args_parser)

  settings = topology.defaults
  if common.QUIET:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  external_commands.run_probes(settings,topology.provider,2)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])
  provider.call('pre_output_transform',topology)

  if hasattr(provider,'pre_start_lab') and callable(provider.pre_start_lab):
    provider.pre_start_lab(topology)

  external_commands.start_lab(settings,topology.provider,3,"netlab up")

  if hasattr(provider,'post_start_lab') and callable(provider.post_start_lab):
    provider.post_start_lab(topology)

  if not args.no_config:
    external_commands.deploy_configs(4,"netlab up",args.fast_config)
    message = get_message(topology,'up',False)
    if message:
      print(f"\n\n{message}")
  else:
    print("\nInitial configuration skipped, run 'netlab initial' to configure the devices")
