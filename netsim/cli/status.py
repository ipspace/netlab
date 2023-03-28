#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import subprocess

from box import Box

from .. import common
from .. import read_topology
from ..utils import status

from . import external_commands

def status_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab status',
    description='Display lab status')
#  parser.add_argument(
#    '-v','--verbose',
#    dest='verbose',
#    action='count',
#    default=0,
#    help='Verbose logging')
  parser.add_argument(
    dest='action',
    action='store',
    choices=['list','show','cleanup','reset'],
    help='Lab status action')
  parser.add_argument(
    dest='instance',
    action='store',
    nargs="*",
    help='Display or cleanup specific lab instance(s)')
  if args:
    return parser.parse_args(args)
  else:
    return parser.parse_args(['list'])

def display_active_labs(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  if not lab_states:
    print('No netlab-managed labs')
    return

  for id,lab_state in lab_states.items():
    print(f'Lab {id} in {lab_state.dir}')
    print(f'  status: {lab_state.status}')
    print(f'  provider(s): {",".join(lab_state.providers)}')
    print()

  for provider,pdata in topology.defaults.providers.items():
    if not 'act_probe' in pdata:
      continue
    try:
      result = subprocess.run(pdata.act_probe.split(' '),capture_output=True,text=True)
    except:
      continue
    if result.stdout:
      print(f'{pdata.act_title}\n{"=" * 80}\n{result.stdout}\n')

def show_lab_instance(lab_state: Box) -> None:
  print(f'Lab {lab_state.id} in {lab_state.dir}')
  print(f'  status: {lab_state.status}')
  print(f'  provider(s): {",".join(lab_state.providers)}')
  if lab_state.log:
    newline = "\n"
    print(f'\nLog:\n{"=" * 80}\n{newline.join(lab_state.log)}{newline}')

def show_lab(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  for iid in args.instance:
    if not iid in lab_states:
      print(f'Unknown lab instance {iid}, skipping\n')
      continue
    show_lab_instance(lab_states[iid])

action_map = {
  'list': display_active_labs,
  'show': show_lab,
#  'cleanup': cleanup_lab,
#  'reset': reset_lab_status
}

def run(cli_args: typing.List[str]) -> None:
  topology = read_topology.load("package:cli/empty.yml","","package:topology-defaults.yml")
  lab_states = status.read_status(topology)
  args = status_parse(cli_args)
  common.set_logging_flags(args)
  if args.action in action_map:
    action_map[args.action](topology,args,lab_states)
  else:
    common.fatal(f'Unknown action {args.action}')
    return
