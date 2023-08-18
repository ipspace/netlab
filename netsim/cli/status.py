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

from ..utils import status, strings, log, read as _read

from . import external_commands
from . import down

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
  parser.add_argument(
    '--all',
    dest='all',
    action='store_true',
    help='Display or cleanup all lab instance(s)')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose printout(s)')
  if args:
    return parser.parse_args(args)
  else:
    return parser.parse_args(['list'])

def display_active_labs(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  if args.verbose:
    print(f'netlab status file: {status.get_status_filename(topology)}\n')
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

def show_lab_instance(iid: str, lab_state: Box) -> None:
  print(f'Lab {iid} in {lab_state.dir}')
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

  for iid in lab_states.keys():
    if not iid in args.instance and not args.all:
      continue
    show_lab_instance(iid,lab_states[iid])

def cleanup_lab(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  if args.all:
    print(f'Active lab instances:\n')
    for k,v in lab_states.items():
      print (f'  {k} in {v.dir}')
    print("")
  
  if not args.all and not args.instance:
    print('No lab instances specified, nothing to do')
    return
  confirm_msg = f'Cleanup will remove all {"" if args.all else "specified "}lab instances. Are you sure?'
  if not strings.confirm(confirm_msg):
    return

  pwd = os.getcwd()
  for iid in list(lab_states.keys()):
    if not args.all and not iid in args.instance:
      continue
    print(f'Shutting down lab {iid} in {lab_states[iid].dir}')
    os.chdir(lab_states[iid].dir)
    try:
      result = subprocess.run(['netlab','down','--cleanup'],capture_output=False,check=True)
    except Exception as ex:
      print(f'Error shutting down lab {iid}: {ex}')
      print(f'... aborting the cleanup process')
      break

  os.chdir(pwd)

def reset_lab_status(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  lab_status_file = status.get_status_filename(topology)
  print(f'''
This action deletes the lab status file {lab_status_file}.

That makes it impossible for netlab to track active lab instances. Use this
command only when you're absolutely sure that the lab status shown by
'netlab status' is corrupted
''')
  if not strings.confirm('Do you want to continue?'):
    return
  try:
    os.remove(lab_status_file)
    print('Lab status file removed')
  except Exception as ex:
    log.fatal(f'Cannot remove lab status file: {ex}')

action_map = {
  'list': display_active_labs,
  'show': show_lab,
  'cleanup': cleanup_lab,
  'reset': reset_lab_status
}

def run(cli_args: typing.List[str]) -> None:
  topology = _read.system_defaults()
  lab_states = status.read_status(topology)
  args = status_parse(cli_args)
  log.set_logging_flags(args)
  if args.action in action_map:
    action_map[args.action](topology,args,lab_states)
  else:
    log.fatal(f'Unknown action {args.action}')
