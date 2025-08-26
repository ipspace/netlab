#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import os
import subprocess
import sys
import typing

from box import Box

from .. import providers
from ..data import get_empty_box
from ..outputs import common as outputs_common
from ..utils import log, status, strings
from ..utils import read as _read
from . import parser_add_verbose, parser_lab_location


def status_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab status',
    description='Display lab status')
  parser.add_argument(
    '-l','--log',
    dest='log',
    action='store_true',
    help='Display the lab instance event log')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Cleanup the current or specified lab instance')
  parser.add_argument(
    '--reset',
    dest='reset',
    action='store_true',
    help='Reset the lab instance tracking system')
  parser.add_argument(
    '--all',
    dest='all',
    action='store_true',
    help='Display an overview of all lab instance(s)')
  parser_add_verbose(parser)
  parser_lab_location(parser,instance=True,action='inspect')
  return parser.parse_args(args)

Lab_Instance_ID = typing.Union[str,int]

def get_instance(args: argparse.Namespace, lab_states: Box) -> Lab_Instance_ID:
  if args.instance:
    instance_id = int(args.instance) if args.instance.isdigit() else args.instance
    if not instance_id in lab_states:
      log.error(
        f"Unknown lab instance {args.instance}.",
        category=log.FatalError,
        module='',
        more_hints="Use 'netlab status --all' to display the list of lab instances")
      sys.exit(1)
    return instance_id

  try:
    cur_dir = os.getcwd()
  except Exception as ex:
    log.fatal(f'Cannot get current directory: {ex}','')
  for id,state in lab_states.items():
    if state.dir == cur_dir:
      return id
    
  log.error(
    f"There's no running lab in the current directory.",
    category=log.FatalError,
    module='',
    more_hints="Use 'netlab status --all' to display the list of lab instances")
  sys.exit(1)

def display_active_labs(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  if args.verbose:
    print(f'netlab status file: {status.get_status_filename(topology)}\n')

  print("Active lab instance(s)\n")
  heading = [ 'id', 'directory', 'status', 'providers' ]
  rows = []
  for id,lab_state in lab_states.items():
    line = [str(id),lab_state.dir,lab_state.status or 'Unknown',",".join(lab_state.providers)]
    rows.append(line)

  strings.print_table(heading,rows)

def show_lab_instance(iid: Lab_Instance_ID, lab_state: Box) -> None:
  print(f'Lab {iid} in {lab_state.dir}')
  print(f'  status: {lab_state.status}')
  print(f'  provider(s): {",".join(lab_state.providers)}')
  print()

def load_provider_status(p_status: dict, provider: str, topology: Box) -> None:
  p_module = providers.get_provider_module(topology,provider)

  if not provider in p_status:
    p_status[provider] = p_module.call('get_lab_status') or get_empty_box()

def show_lab_nodes(topology: Box) -> None:
  p_status: dict = {}
  rows = []
  heading = [ 'node', 'device', 'image', 'mgmt IPv4', 'connection', 'provider', 'VM/container', 'status']

  for n_name,n_data in topology.nodes.items():
    n_ext = outputs_common.adjust_inventory_host(
              node=topology.nodes[n_name],
              defaults=topology.defaults,
              group_vars=True)

    n_provider = n_data.get('provider',topology.defaults.provider)
    p_module   = providers.get_provider_module(topology,n_provider)
    load_provider_status(p_status,n_provider,topology)

    if n_data.get('unmanaged',False):
      row = [ n_data.name, n_data.device, 'unmanaged', n_data.mgmt.ipv4 ]
    else:
      row = [ n_data.name, n_data.device, n_data.box, n_data.mgmt.ipv4, n_ext.ansible_connection, n_provider ]
      wk_name = p_module.call('get_node_name',n_name,topology)
      row.append(wk_name)

      wk_state = p_status[n_provider].get(wk_name,None) or p_status[n_provider].get(n_name,None)
      row.append(wk_state.status if wk_state else 'Unknown')

    rows.append(row)

  for t_name,t_data in topology.tools.items():
    n_provider = 'clab'
    load_provider_status(p_status,n_provider,topology)

    wk_name = f'{topology.name}_{t_name}'
    wk_state = p_status[n_provider].get(wk_name,get_empty_box())

    row = [ t_name, '(tool)', wk_state.get('image',''), '', 'docker', n_provider, 
            wk_name, wk_state.get('status','Not running') ]
    rows.append(row)

  strings.print_table(heading,rows)

def print_lab_log(log: typing.List) -> None:
  if not log:
    return

  newline = "\n"
  print(f'{newline.join(log)}{newline}')

def get_lab_status(lab_state: Box) -> str:
  if lab_state.status == 'started':
    return lab_state.status

  for line in lab_state.log:
    if 'started' in line:
      return line

  return lab_state.status

def show_lab(args: argparse.Namespace,lab_states: Box) -> None:
  iid = get_instance(args,lab_states)
  lab_state = lab_states[iid]
  show_lab_instance(iid,lab_state)
  wdir = lab_state.dir
  snapshot = f'{wdir}/netlab.snapshot.yml'

  topology = _read.read_yaml(filename=snapshot)
  if topology is None:
    log.fatal(f'Cannot read topology snapshot file {snapshot}')

  lab_status = get_lab_status(lab_state)
  if 'started' not in lab_status:
    log.error(
      'Lab is not started, cannot display node/tool status. Displaying lab start/stop log',
      category=log.FatalError,
      module='',)
    print()
    print_lab_log(lab_state.log)
    return

  show_lab_nodes(topology)
  if lab_status != 'started':
    print()
    log.warning(
      text="Lab is not in 'started' state, inspect details with 'netlab status --log'",
      module='-')

def show_lab_log(args: argparse.Namespace, lab_states: Box) -> None:
  iid = get_instance(args,lab_states)
  lab_state = lab_states[iid]
  show_lab_instance(iid,lab_state)
  print_lab_log(lab_state.log)

def cleanup_lab(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  iid = get_instance(args,lab_states)

  confirm_msg = f'Cleanup will remove lab instance "{ iid }" in {lab_states[iid].dir}. Are you sure?'
  try:
    if not strings.confirm(confirm_msg):
      return
  except KeyboardInterrupt:
    print("")
    log.fatal('User interrupt, exiting...')

  print(f'Shutting down lab {iid} in {lab_states[iid].dir}')
  os.chdir(lab_states[iid].dir)
  try:
    subprocess.run(['netlab','down','--cleanup'],capture_output=False,check=True)
  except Exception as ex:
    log.error(
      f'Error shutting down lab {iid}: {ex}',
      category=log.FatalError,
      module='',
      more_hints = f'Change directory to { os.getcwd() } and execute "netlab down --cleanup --force"')

def reset_lab_status(topology: Box) -> None:
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

def check_conflicting_options(args: argparse.Namespace) -> None:
  var_args = vars(args)
  kw_list = [ '--'+kw for kw in ('all','reset','cleanup') if kw in var_args and var_args[kw] ]
  if len(kw_list) > 1:
    log.fatal(f"You can use only one of the {', '.join(kw_list)} options")

def run(cli_args: typing.List[str]) -> None:
  args = status_parse(cli_args)
  log.set_logging_flags(args)
  check_conflicting_options(args)

  topology = _read.system_defaults()
  if args.reset:
    reset_lab_status(topology)
    return

  lab_states = status.read_status(topology)
  if not lab_states:
    print('No netlab-managed labs')
    sys.exit(1)

  if args.all:
    display_active_labs(topology,args,lab_states)
  elif args.cleanup:
    cleanup_lab(topology,args,lab_states)
  elif args.log:
    show_lab_log(args,lab_states)
  else:
    show_lab(args,lab_states)
