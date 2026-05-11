#
# netlab restart command
#
# Perform 'netlab down' followed by 'netlab up'
#
import argparse
import typing

from ..utils import log
from . import common_parse_args, down, load_snapshot, parser_lab_location, up


#
# Extra arguments for 'netlab up' command
#
def restart_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(
    prog="netlab restart",
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
  parser_lab_location(parser,instance=True,snapshot=True,action='restart')
  return parser

def down_args(args: argparse.Namespace, with_snapshot: bool = False) -> list:
  args_list = []
  if args.verbose:
    args_list.append("-" + "v" * args.verbose)
  if args.snapshot and with_snapshot:
    args_list += ["--snapshot", args.snapshot]
  return args_list

def up_args(args: argparse.Namespace, topo_name: str) -> list:
  args_list = down_args(args,with_snapshot=False)
  if args.quiet:
    args_list.append("-q")
  if args.no_config:
    args_list.append('--no-config')
  if args.fast_config:
    args_list.append('--fast-config')
  args_list.append(topo_name)
  return args_list

def run(cli_args: typing.List[str]) -> None:
  parser = restart_parse_args()
  args = parser.parse_args(cli_args)
  log.set_logging_flags(args)
  topology = load_snapshot(args,warn_modified=False)
  if not topology:
    log.fatal(f'Cannot read the snapshot file {args.snapshot}')
  try:
    topo_name = topology.get('input',[])[0]
  except Exception as ex:
    log.fatal(f'Cannot find the original topology name from the snapshot file: {str(ex)}')

  down.run(down_args(args,with_snapshot=True))
  log.section_header('Progress','Lab has been stopped, starting new instance',color='bright_cyan')
  up.run(up_args(args,topo_name))
