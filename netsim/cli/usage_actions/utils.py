#
# netlab usage utility commands
#
import argparse

from ...data import get_box
from ...utils import log, stats, strings


def is_enabled(flag: bool) -> str:
  return 'enabled' if flag else 'disabled'

def confirm_parser(parser: argparse.ArgumentParser) -> None:
  parser.add_argument(
    '-y','--yes',
    dest='confirm',
    action='store_true',
    help='Confirm action with a CLI parameter')

"""
Stop collecting usage statistics
"""
def usage_stop(args: argparse.Namespace) -> None:
  s_data = stats.read_stats()
  s_disabled = s_data.get('_disabled',False)
  if s_disabled:
    log.info('The collection of usage statistics is already disabled',module='usage')
    return

  if not args.confirm and not strings.confirm('Do you want to stop collecting the usage statistics'):
    return

  stats.stats_change_data({'_disabled': True})
  log.info('Collecting of usage statistics has been disabled',module='usage')

"""
Start collecting usage statistics
"""
def usage_start(args: argparse.Namespace) -> None:
  s_data = stats.read_stats()
  s_disabled = s_data.get('_disabled',False)
  hints = [
      'The statistics are not shared with anyone.',
      'You can view them with "netlab usage show" command']
  if not s_disabled:
    log.info('The collection of usage statistics is already active',module='usage',more_hints=hints)
    return

  if not args.confirm and not strings.confirm('Do you want to start collecting local usage statistics'):
    return

  stats.stats_change_data({'_disabled': False})
  log.info(
    text='Collecting of usage statistics is enabled',module='usage',more_hints=hints)

def usage_clear(args: argparse.Namespace) -> None:
  s_data = stats.read_stats()
  if not s_data:
    log.info(
      text='No usage statistics have been collected',
      module='usage')
    return

  s_disabled = s_data.get('_disabled',False)
  if not args.confirm and not strings.confirm('Do you want to clear the usage statistics'):
    return
  
  s_data = get_box({'_disabled': s_disabled})
  stats.write_stats(s_data,force=True)
  log.info(
    text=f'Statistics cleared. Collection of usage statistics is {is_enabled(not s_disabled)}',
    module='usage')
