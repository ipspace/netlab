#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import typing

from ..utils import log
from ..utils import read as _read
from . import parser_subcommands, subcommand_usage
from .clab_actions import build as _build
from .clab_actions import cleanup as _cleanup
from .clab_actions import tarball as _tarball

clab_dispatch: dict = {
  'tarball': {
    'exec':  _tarball.clab_tarball,
    'parser': _tarball.tarball_parser,
    'description': 'Create a tar archive from the current clab/device configuration'
  },
  'build': {
    'exec':  _build.clab_build,
    'parser': _build.build_parser,
    'description': 'Build a routing daemon Docker container'
  },
  'cleanup': {
    'exec': _cleanup.clab_cleanup,
    'parser': _cleanup.cleanup_parser,
    'description': 'Remove running containers and Docker networks'
  }
}

def clab_parse(args: typing.List[str]) -> argparse.Namespace:
  global clab_dispatch

  parser = argparse.ArgumentParser(
    prog="netlab clab",
    description='Containerlab utilities',
    epilog="Use 'netlab clab subcommand -h' to get subcommand usage guidelines")
  parser_subcommands(parser,clab_dispatch)

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  settings = _read.read_yaml('package:topology-defaults.yml')
  if not settings:
    log.fatal("Cannot read the system defaults","clab")

  if not cli_args:
    subcommand_usage(clab_dispatch)
    return

  args = clab_parse(cli_args)
  args.execute(args,settings)
