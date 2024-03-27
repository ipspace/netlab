#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import string
import pathlib
import glob
import subprocess
import shutil

from box import Box

from ..utils import files as _files, log, strings, read as _read
from . import external_commands
from . import collect
from . import fs_cleanup
from .clab_actions import clab_usage
from .clab_actions.build import clab_build
from .clab_actions.tarball import clab_tarball

def run(cli_args: typing.List[str]) -> None:
  settings = _read.read_yaml('package:topology-defaults.yml')
  if not cli_args:
    clab_usage()
    return

  if not settings:
    log.fatal("Cannot read the system defaults","clab")

  if cli_args[0] == 'tarball':
    clab_tarball(cli_args[1:],settings)
  elif cli_args[0] == 'build':
    clab_build(cli_args[1:],settings)
  else:
    clab_usage()
