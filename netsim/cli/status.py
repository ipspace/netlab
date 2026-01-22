#
# netlab status command
#
# Display the status of the specified lab or system-wide status
#
import argparse
import os
import subprocess
import sys
import typing

from box import Box

from .. import providers
from ..data import get_box, get_empty_box
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
    '--format',
    dest='format',
    action='store',
    choices=['json','yaml','text'],
    default='text',
    help='Specify the output format')
  parser.add_argument(
    '--all',
    dest='all',
    action='store_true',
    help='Display an overview of all lab instance(s)')
  parser_add_verbose(parser)
  parser_lab_location(parser,instance=True,action='inspect')
  return parser.parse_args(args)

Lab_Instance_ID = typing.Union[str,int]

OUTPUT_FORMAT: str = 'text'

def raise_error(text: str, fatal: bool = False,**kwargs: typing.Any) -> None:
  global OUTPUT_FORMAT
  if OUTPUT_FORMAT != 'text':
    raise log.ErrorAbort(text)
  if 'module' not in kwargs:
    kwargs['module'] = 'status'
  log.error(text,**kwargs)
  if fatal or kwargs.get('category',None) == log.FatalError:
    sys.exit(1)

  return

def print_result(r: Box, fmt: str) -> None:
  if fmt == 'json':
    print(r.to_json(skipkeys=True,indent=2))
  elif fmt == 'yaml':
    print(r.to_yaml())
  else:
    raise_error(f'Invalid output format {fmt}',category=log.FatalError)

def get_instance(args: argparse.Namespace, lab_states: Box) -> Lab_Instance_ID:
  if args.instance:
    instance_id = int(args.instance) if args.instance.isdigit() else args.instance
    if not instance_id in lab_states:
      raise_error(
        f"Unknown lab instance {args.instance}",
        category=log.FatalError,
        module='',
        more_hints="Use 'netlab status --all' to display the list of lab instances")
      sys.exit(1)                                 # We'll never get here, but mypy won't complain
    return instance_id

  try:
    cur_dir = os.getcwd()
  except Exception as ex:
    raise_error(
      f'Cannot get current directory: {str(ex)}',
      category=log.FatalError)

  for id,state in lab_states.items():
    if state.dir == cur_dir:
      return id
    
  raise_error(
    f"There's no running lab in the current directory.",
    category=log.FatalError,
    module='',
    more_hints="Use 'netlab status --all' to display the list of lab instances")
  sys.exit(1)                                     # To keep mypy happy ;)

def cleanup_state(ls: Box, iid: typing.Optional[typing.Union[int,str]] = None) -> Box:
  if iid is not None:
    ls.instance = iid

  if 'timestamp' in ls:
    ls.timestamp = str(ls.timestamp)

  return ls

def display_active_labs(topology: Box,args: argparse.Namespace,lab_states: Box) -> None:
  if args.verbose:
    print(f'netlab status file: {status.get_status_filename(topology)}\n')

  if args.format != 'text':
    result = get_box({ k:cleanup_state(v) for k,v in lab_states.items() })
    print_result(result,args.format)
    return

  print("Active lab instance(s)\n")
  heading = [ 'id', 'directory', 'status', 'providers' ]
  rows = []
  for id,lab_state in lab_states.items():
    line = [str(id),lab_state.dir,lab_state.status or 'Unknown',",".join(lab_state.providers)]
    rows.append(line)

  strings.print_table(heading,rows)

def show_lab_instance(iid: Lab_Instance_ID, lab_state: Box) -> None:
  print(f'Lab {iid} in {lab_state.dir}')
  if lab_state.status:
    print(f'  status: {lab_state.status}')
  if lab_state.providers:
    print(f'  provider(s): {",".join(lab_state.providers)}')
  print()

def load_provider_status(p_status: dict, provider: str, topology: Box) -> None:
  p_module = providers.get_provider_module(topology,provider)

  if not provider in p_status:
    p_status[provider] = p_module.call('get_lab_status') or get_empty_box()

def fetch_node_status(ls: Box, topology: Box) -> None:
  p_status: dict = {}
  for n_name,n_data in topology.nodes.items():
    n_ext = outputs_common.adjust_inventory_host(
              node=topology.nodes[n_name],
              defaults=topology.defaults,
              group_vars=True)

    n_provider = n_data.get('provider',topology.defaults.provider)
    p_module   = providers.get_provider_module(topology,n_provider)
    load_provider_status(p_status,n_provider,topology)

    ls.nodes[n_name] = {
      'device': n_data.device,
      'mgmt':   n_data.mgmt.ipv4
    }
    node_stat = ls.nodes[n_name]
    node_stat.connection = n_ext.ansible_connection
    if n_data.get('unmanaged',False):
      node_stat.image = 'unmanaged'
      node_stat.provider = 'unmanaged'
      node_stat.status = 'Unknown'
    else:
      node_stat.image = n_data.box
      node_stat.provider = n_provider
      wk_name = p_module.call('get_node_name',n_name,topology)
      node_stat.provider_name = wk_name
      wk_state = p_status[n_provider].get(wk_name,None) or p_status[n_provider].get(n_name,None)
      node_stat.status = wk_state.get('status','Unknown')

  for t_name,t_data in topology.tools.items():
    n_provider = 'clab'
    load_provider_status(p_status,n_provider,topology)

    wk_name = f'{topology.name}_{t_name}'
    wk_state = p_status[n_provider].get(wk_name,get_empty_box())
    ls.nodes[t_name] = {
      'device': '(tool)',
      'image': wk_state.get('image',''),
      'connection': 'docker',
      'provider': n_provider,
      'provider_name': wk_name,
      'status': wk_state.get('status','Not running')
    }

def show_lab_nodes(ls: Box, topology: Box) -> None:
  rows = []
  heading = [ 'node', 'device', 'image', 'mgmt IPv4', 'connection', 'provider', 'VM/container', 'status']

  for n_name,n_data in ls.nodes.items():
    row = [ n_name, n_data.device, n_data.image, n_data.get('mgmt',''),
            n_data.connection, n_data.get('provider',''),
            n_data.get('provider_name',''), n_data.status ]
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
      lab_state.status = line
      return line

  return lab_state.status

def show_lab(args: argparse.Namespace,lab_states: Box) -> None:
  iid = get_instance(args,lab_states)
  lab_state = cleanup_state(lab_states[iid])
  wdir = lab_state.dir
  snapshot = f'{wdir}/netlab.snapshot.pickle'

  topology = _read.load_pickled_data(snapshot)
  if topology is None:
    log.fatal(f'Cannot read topology snapshot file {snapshot}')

  lab_status = get_lab_status(lab_state)
  if 'started' not in lab_status:
    err = 'Lab is not started, cannot display node/tool status'
    if args.format == 'text':
      err += '. Displaying lab start/stop log'
    raise_error(err, category=log.MissingValue,module='')
    print()
    show_lab_instance(iid,lab_state)
    print_lab_log(lab_state.log)
    return

  fetch_node_status(lab_state,topology)
  if args.format != 'text':
    print_result(lab_state,args.format)
    return

  show_lab_instance(iid,lab_state)
  show_lab_nodes(lab_state,topology)
  if lab_status != 'started':
    print()
    log.warning(
      text="Lab is not in 'started' state, inspect details with 'netlab status --log'",
      module='-')

def show_lab_log(args: argparse.Namespace, lab_states: Box) -> None:
  iid = get_instance(args,lab_states)
  lab_state = lab_states[iid]
  if args.format != 'text':
    print_result(cleanup_state(lab_state,iid),fmt=args.format)
    return

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

  lab_dir = lab_states[iid].dir
  print(f'Shutting down lab {iid} in {lab_dir}')
  try:
    os.chdir(lab_dir)
  except Exception as ex:
    log.error(
      f'Cannot change directory to {lab_dir}',
      more_data=[ str(ex) ],
      category=log.FatalError)
    print(f'''
It looks like something messed up the directory in which the lab was running. If
that's the case, the only way to recover from this condition is to shut down all
other lab instances, reset the instance tracking system with 'netlab status
--reset' and clean up the remaining containers and virtual machines by hand as
the Vagrant and containerlab information has probably been lost.
''')
    sys.exit(1)

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
  no_json = [ '--'+kw for kw in ('reset','cleanup') if kw in var_args and var_args[kw] ]
  if no_json and var_args.get('format','text') != 'text':
    log.fatal(f"Cannot use {no_json[0]} option with JSON or YAML output format")

def no_labs_message(fmt: str) -> typing.NoReturn:
  txt = 'No netlab-managed labs'
  if fmt == 'text':
    print(txt)
  else:
    print_result(get_box({'warning': txt}),fmt)

  sys.exit(1)

def run(cli_args: typing.List[str]) -> None:
  global OUTPUT_FORMAT

  args = status_parse(cli_args)
  log.set_logging_flags(args)
  check_conflicting_options(args)
  OUTPUT_FORMAT = args.format

  try:
    topology = _read.system_defaults()
    if args.reset:
      reset_lab_status(topology)
      return

    lab_states = status.read_status(topology)
    if not lab_states:
      no_labs_message(args.format)

    if args.all:
      display_active_labs(topology,args,lab_states)
    elif args.cleanup:
      cleanup_lab(topology,args,lab_states)
    elif args.log:
      show_lab_log(args,lab_states)
    else:
      show_lab(args,lab_states)
  except log.ErrorAbort as ex:
    print_result(get_box({'error': str(ex)}),args.format)
