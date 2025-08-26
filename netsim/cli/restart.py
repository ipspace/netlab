#
# netlab restart command
#
# Perform 'netlab down' followed by 'netlab up'
#
import argparse
import typing

from . import common_parse_args, down, parser_lab_location, up


#
# Extra arguments for 'netlab up' command
#
def restart_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    description='Reconfigure and restart the virtual lab',
    parents = [ common_parse_args() ],
    add_help=True)
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
    dest='topology', action='store', nargs='?',
    help='Topology file (default: topology.yml)')
  parser_lab_location(parser,snapshot=True,action='restart')
  return parser

def run(cli_args: typing.List[str]) -> None:
  parser = restart_parse_args()
  parser.parse_args(cli_args)
  up_only_args = ['--fast-config','--no-config','--snapshot']

  down.run([ arg for arg in cli_args if arg not in up_only_args ])
  up.run(cli_args)
