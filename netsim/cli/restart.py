#
# netlab restart command
#
# Perform 'netlab down' followed by 'netlab up'
#
import typing
import argparse

from box import Box

from . import down, up
from . import common_parse_args

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
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    const='netlab.snapshot.yml',
    help='Use netlab snapshot file created by a previous lab run to start the lab')
  parser.add_argument(
    dest='topology', action='store', nargs='?',
    help='Topology file (default: topology.yml)')
  return parser

def run(cli_args: typing.List[str]) -> None:
  parser = restart_parse_args()
  args = parser.parse_args(cli_args)
  up_only_args = ['--fast-config','--no-config']

  down.run([ arg for arg in cli_args if arg not in up_only_args ])
  up.run(cli_args)
