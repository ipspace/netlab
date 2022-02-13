#
# netlab config command
#
# Deploy custom configuration template to network devices
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
from .. import providers

#
# Extra arguments for 'netlab up' command
#
def up_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='netlab up extra arguments',add_help=False)
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
  return parser

def run(cli_args: typing.List[str]) -> None:
  up_args_parser = up_parse_args()
  topology = create.run(cli_args,'up','Create configuration files, start a virtual lab, and configure it',up_args_parser)
  settings = topology.defaults

  (args,rest) = up_args_parser.parse_known_args(cli_args)
  external_commands.run_probes(settings,topology.provider,2)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])

  if hasattr(provider,'pre_start_lab') and callable(provider.pre_start_lab):
    provider.pre_start_lab(topology)

  external_commands.start_lab(settings,topology.provider,3,"netlab up")
  
  if hasattr(provider,'post_start_lab') and callable(provider.post_start_lab):
    provider.post_start_lab(topology)

  if not args.no_config:
    external_commands.deploy_configs(4,"netlab up",args.fast_config)
  else:
    print("\nInitial configuration skipped, run 'netlab initial' to configure the devices")
