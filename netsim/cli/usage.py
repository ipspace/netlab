#
# Manage and display usage statistics
#
import typing
import argparse

from box import Box

from . import external_commands,parser_subcommands,subcommand_usage
from .usage_actions import utils as _usage_utils,show as _usage_show

usage_dispatch: dict = {
  'start': {
    'exec':  _usage_utils.usage_start,
    'parser': _usage_utils.confirm_parser,
    'description': '(re)start collecting local usage statistics'
  },
  'stop': {
    'exec':  _usage_utils.usage_stop,
    'parser': _usage_utils.confirm_parser,
    'description': 'stop collecting usage statistics'
  },
  'clear': {
    'exec':  _usage_utils.usage_clear,
    'parser': _usage_utils.confirm_parser,
    'description': 'clear collected usage statistics'
  },
  'show': {
    'exec':  _usage_show.show_commands,
    'parser': _usage_show.show_parser,
    'description': 'display collected usage statistics'
  }
}

def usage_parse(args: typing.List[str]) -> argparse.Namespace:
  global usage_dispatch

  parser = argparse.ArgumentParser(
    prog="netlab usage",
    description='Display and manage usage statistics',
    epilog="Use 'netlab usage subcommand -h' to get subcommand usage guidelines")
  parser_subcommands(parser,usage_dispatch)

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  if not cli_args:
    subcommand_usage(usage_dispatch)
    return

  args = usage_parse(cli_args)
  args.execute(args)
