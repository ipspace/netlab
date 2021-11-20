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

  external_commands.run_probes(settings,topology.provider)
  external_commands.start_lab(settings,topology.provider,2)

  provider = providers._Provider.load(topology.provider,topology.defaults.providers[topology.provider])
  if hasattr(provider,'start_lab') and callable(provider.start_lab):
    provider.start_lab(topology)

  external_commands.deploy_configs(3)

  step = 4
  if 'groups' in topology:
    for gname,gdata in topology.groups.items():
      if 'config' in gdata:
        for template in gdata.config:
          external_commands.custom_configs(template,gname,step)
          step = step + 1
