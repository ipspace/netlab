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

def run(cli_args: typing.List[str]) -> None:
  topology = create.run(cli_args,'up','Create configuration files, start a virtual lab, and configure it')
  settings = topology.defaults

  external_commands.run_probes(settings,topology.provider,2)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])

  if hasattr(provider,'pre_start_lab') and callable(provider.pre_start_lab):
    provider.pre_start_lab(topology)

  external_commands.start_lab(settings,topology.provider,3,"netlab up")
  
  if hasattr(provider,'post_start_lab') and callable(provider.post_start_lab):
    provider.post_start_lab(topology)

  external_commands.deploy_configs(4,"netlab up")
