#
# netlab up command
#
# * Transform lab topology and create provider and automation files,
#   or read transformed lab topology from snapshot file
# * Start the lab, including provider-specific pre- and post-start hooks
#
import typing
import argparse
import os

from box import Box
from pathlib import Path

from . import create
from . import external_commands, set_dry_run, is_dry_run
from . import common_parse_args, get_message
from . import lab_status_update, lab_status_change
from .. import providers
from ..utils import log,status as _status, read as _read

#
# Extra arguments for 'netlab up' command
#
def up_parse_args(standalone: bool) -> argparse.ArgumentParser:
  parse_parents = [ common_parse_args() ] if standalone else []
  parser = argparse.ArgumentParser(
    description='netlab up extra arguments',
    parents = parse_parents,
    add_help=standalone)
  parser.add_argument(
    '--no-config',
    dest='no_config',
    action='store_true',
    help='Do not configure lab devices')
  parser.add_argument(
    '--no-tools',
    dest='no_tools',
    action='store_true',
    help='Do not start the external tools')
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help='Print the commands that would be executed, but do not execute them')
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
    help='Use netlab snapshot file created by a previous lab run')
  return parser

"""
Get lab topology from the snapshot file or run the transformation process
"""
def get_topology(args: argparse.Namespace, cli_args: typing.List[str]) -> Box:
  up_args_parser = up_parse_args(bool(args.snapshot))         # (re)create the correct parser

  if args.snapshot:                                           # If we're using the snapshot file...
    args = up_args_parser.parse_args(cli_args)                # ... and reparse
    log.set_logging_flags(args)                               # ... use these arguments to set logging flags and read the snapshot

    topology = _read.read_yaml(filename=args.snapshot)
    if topology is None:
      log.fatal(f'Cannot read snapshot file {args.snapshot}, aborting...')

    print(f"Using transformed lab topology from snapshot file {args.snapshot}")
  else:                                                       # No snapshot file, use 'netlab create' parser
    topology = create.run(cli_args,'up','Create configuration files, start a virtual lab, and configure it',up_args_parser)

  return topology

"""
Lab status routines:

* status_start_lab -- lab initialization has started
* status_start_provider -- provider activation has started
* status_config -- configuration deployment has started
* status_complete -- lab initialization has completed
"""

def lab_status_start(status: Box, topology: Box) -> None:
  lab_id = _status.get_lab_id(topology)                     # Get the lab ID (or default)
  if lab_id in status:
    if status[lab_id].dir != os.getcwd():
      lab_status_update(topology,status,
        update = { 'status': f'conflict -- trying to start lab in {os.getcwd()}'})
      topology.defaults.err_conflict = status[lab_id].dir
      return

  lab_status_update(topology,status,
    update = {
      'status': 'starting lab' if not lab_id in status else 'restarting lab',
      'name': topology.name,
      'providers': [] })

def status_start_lab(topology: Box) -> None:
  _status.change_status(
    topology,
    callback = lambda s,t: lab_status_start(s,t))

def status_start_provider(topology: Box, provider: str) -> None:
  _status.change_status(
    topology,
    callback = lambda s,t: 
      lab_status_update(t,s,
        update = { 'status': f'starting provider {provider}' },
        cb = lambda s: s.providers.append(provider)))

"""
check_existing_lab -- print an command-specific error message if there'a s lab already running in this directory
"""
def check_existing_lab() -> None:
  if not _status.is_directory_locked():
    return
  
  print(f'''
It looks like you have another lab running in this directory. If you want to
continue the lab startup process due to a previous failure, please use the
'netlab up --snapshot' command.

Otherwise use 'netlab status' to check the status of labs running on this machine, or
'netlab down' to shut down the other lab running in this directory.

If you are sure that no other lab is running in this directory, remove the
netlab.lock file manually and retry.
''')
  log.fatal('Cannot start another lab in the same directory')

"""
check_lab_instance -- print an error message if the lab instance is already running in a different directory
"""
def check_lab_instance(topology: Box) -> None:
  lab_id = _status.get_lab_id(topology)           # Get the current lab instance ID from lab topology
  lab_states = _status.read_status(topology)      # Read the state of existing lab instances

  if not lab_id in lab_states:                    # If this lab instance is not running ==> OK
    return
  
  if lab_states[lab_id].dir == os.getcwd():       # If this lab instance is already running in this directory
    return                                        # ... we'll deal with that a bit later in the process

  print(f'''
It looks like the lab instance '{lab_id}' is already running in directory
{lab_states[lab_id].dir}.

Please use 'netlab status' to check the status of labs running on this machine.
You can stop the other lab instance with 'netlab status cleanup {lab_id}'.

If you think your netlab status file is corrupt, use 'netlab status reset' to
delete it.
''')
  log.fatal(f'aborting "netlab up" request')

"""
Execute provider probes
"""
def provider_probes(topology: Box, step: int = 2) -> None:
  p_provider = topology.provider

  external_commands.run_probes(topology.defaults,p_provider,step)
  for s_provider in topology[p_provider].providers:
    external_commands.run_probes(topology.defaults,s_provider,step)

"""
Start lab topology for a single provider
"""
def start_provider_lab(topology: Box, pname: str, sname: typing.Optional[str] = None) -> None:
  p_name   = sname or pname
  p_module = providers._Provider.load(p_name,topology.defaults.providers[p_name])

  if sname is not None:
    p_topology = providers.select_topology(topology,p_name)
  else:
    p_topology = topology

  status_start_provider(topology,p_name)
  p_module.call('pre_start_lab',p_topology)
  if sname is not None:
    exec_command = topology.defaults.providers[pname][sname].start
  else:
    exec_command = topology.defaults.providers[pname].start

  exec_list = exec_command if isinstance(exec_command,list) else [ exec_command ]
  for cmd in exec_list:
    print(f"provider {p_name}: executing {cmd}")
    if not external_commands.run_command(cmd):
      log.fatal(f"{cmd} failed, aborting...","netlab up")

  p_module.call('post_start_lab',p_topology)

  lab_status_change(topology,f'{p_name} workload started')

"""
Recreate secondary configuration file
"""
def recreate_secondary_config(topology: Box, p_provider: str, s_provider: str) -> None:
  sp_data = topology.defaults.providers[p_provider][s_provider]
  if not sp_data.recreate_config:                                     # Do we need to recreate the config file?
    return

  sp_module  = providers._Provider.load(s_provider,topology.defaults.providers[s_provider])
  s_topology = providers.select_topology(topology,s_provider)         # Create secondary provider subtopology
  filename = sp_data.filename                                         # Get the secondary configuration filename
  print(f"Recreating {filename} configuration file for {s_provider} provider")
  sp_module.create(s_topology,filename)                               # ... and create the new configuration file

"""
Deploy initial configuration
"""
def deploy_initial_config(args: argparse.Namespace, topology: Box, step: int) -> None:
  if args.no_config:
    print("\nInitial configuration skipped, run 'netlab initial' to configure the devices")
    return

  lab_status_change(topology,f'deploying initial configuration')
  external_commands.deploy_configs(step,"netlab up",args.fast_config)
  message = get_message(topology,'up',False)
  if message:
    print(f"\n\n{message}")
  lab_status_change(topology,f'initial configuration complete')

"""
Deploy external tools
"""
def start_external_tools(args: argparse.Namespace, topology: Box, step: int) -> None:
  if not 'tools' in topology:
    return
  if args.no_tools:
    print("\nExternal tools not started, start them manually")
    return

  external_commands.print_step(step,f"Starting external tools")
  lab_status_change(topology,f'starting external tools')
  for tool in topology.tools.keys():
    cmds = external_commands.get_tool_command(tool,'up',topology)
    if cmds is None:
      continue
    external_commands.execute_tool_commands(cmds,topology)
    msg = external_commands.get_tool_message(tool,topology)
    if not is_dry_run():
      print(f"... {tool} tool started")

    if msg:
      print(("DRY_RUN: " if is_dry_run() else "") + msg + "\n")

  lab_status_change(topology,f'external tools started')

"""
Main "lab start" process
"""
def run(cli_args: typing.List[str]) -> None:
  up_args_parser = up_parse_args(False)                       # Try to parse the up-specific arguments
  (args,rest) = up_args_parser.parse_known_args(cli_args)
  set_dry_run(args)
  if not args.snapshot and not is_dry_run():
    check_existing_lab()

  topology = get_topology(args,cli_args)
  if not is_dry_run():
    check_lab_instance(topology)

  settings = topology.defaults
  if log.QUIET:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  provider_probes(topology)

  p_provider = topology.provider
  p_module = providers._Provider.load(p_provider,topology.defaults.providers[p_provider])
  providers.mark_providers(topology)
  p_module.call('pre_output_transform',topology)

  status_start_lab(topology)
  if 'err_conflict' in topology.defaults:
    log.fatal(f'race condition, lab instance already running in {topology.defaults.err_conflict}')

  if not is_dry_run():
    _status.lock_directory()

  step = 3
  external_commands.print_step(step,f"Starting the lab: {p_provider}")
  start_provider_lab(topology,p_provider)

  for s_provider in topology[p_provider].providers:
    step += 1
    external_commands.print_step(step,f"Starting the lab: {s_provider}",spacing=True)
    recreate_secondary_config(topology,p_provider,s_provider)
    start_provider_lab(topology,p_provider,s_provider)

  deploy_initial_config(args,topology,step+1)
  start_external_tools(args,topology,step+2)
  lab_status_change(topology,'started')
