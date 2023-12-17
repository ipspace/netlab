#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import textwrap
import sys
from box import Box

from .. import data
from ..augment import main
from ..utils import log,read as _read
from .usage import print_usage

from .show_commands import show_common_parser
from .show_commands import devices as _devices
from .show_commands import images as _images
from .show_commands import modules as _modules
from .show_commands import module_support as _mod_support
from .show_commands import outputs as _outputs
from .show_commands import reports as _reports
from .show_commands import providers as _providers
from .show_commands import attributes as _attributes
from .show_commands import defaults as _defaults

show_dispatch: dict = {
  'images': {
    'exec':  _images.show,
    'parse': _images.parse
  },
  'devices': {
    'exec':  _devices.show,
    'parse': _devices.parse
  },
  'module-support': {
    'exec':  _mod_support.show,
    'parse': _mod_support.parse
  },
  'modules': {
    'exec':  _modules.show,
    'parse': _modules.parse
  },
  'outputs': {
    'exec':  _outputs.show,
    'parse': _outputs.parse
  },
  'reports': {
    'exec':  _reports.show,
    'parse': _reports.parse
  },
  'providers': {
    'exec':  _providers.show,
    'parse': _providers.parse
  },
  'attributes': {
    'exec':  _attributes.show,
    'parse': _attributes.parse
  },
  'defaults': {
    'exec':  _defaults.show,
    'parse': _defaults.parse
  }
}

def show_usage(err: bool = False) -> typing.NoReturn:
  print_usage('show-usage.txt')
  sys.exit(1 if err else 0)

def parse_show_args(cli_args: typing.List[str]) -> argparse.Namespace:
  if not len(cli_args):
    show_usage()

  if len(cli_args) == 1 and cli_args[0] in ('help','-h'):
    show_usage()

  action = cli_args.pop(0)
  if not action in show_dispatch:
    log.fatal("Unknown request, use 'netlab show' to display valid options")

  if 'parse' in show_dispatch[action]:
    parser = show_dispatch[action]['parse']()
  else:
    parser = show_common_parser(action,'system parameters')

  args = parser.parse_args(cli_args)
  args.action = action
  return args

def run(cli_args: typing.List[str]) -> None:
  global show_dispatch

  args = parse_show_args(cli_args)

  empty_file = "package:cli/empty.yml"
  user_defaults: typing.Optional[list] = [] if 'system' in args and args.system else None
  topology = _read.load(empty_file,user_defaults=user_defaults)

  if topology is None:
    log.fatal("Cannot read system settings")
    return

  log.init_log_system(False)
  topology.name = 'empty'
#  topology.nodes = data.get_empty_box()
  topology.nodes.dummy.device = 'none'                  # Add a dummy node
  topology.nodes.dummy.module = []                      # ... and disable all modules on that node
  if 'plugin' in args and args.plugin:
    topology.plugin = args.plugin

  main.transform_setup(topology)
  settings = topology.defaults
  show_dispatch[args.action]['exec'](settings,args)
