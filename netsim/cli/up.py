#
# netlab up command
#
# * Transform lab topology and create provider and automation files,
#   or read transformed lab topology from snapshot file
# * Start the lab, including provider-specific pre- and post-start hooks
#
import argparse
import os
import re
import sys
import time
import typing

from box import Box

from .. import augment, providers
from ..devices import process_config_sw_check
from ..utils import log, stats, strings
from ..utils import status as _status
from . import (
  common_parse_args,
  create,
  external_commands,
  get_message,
  is_dry_run,
  lab_status_change,
  lab_status_update,
  load_snapshot,
  set_dry_run,
)


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
    '-r','--reload-config',
    dest='reload',
    action='store',
    help='Reload saved configurations from specified directory')
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
    const='netlab.snapshot.pickle',
    help='Use netlab snapshot file created by a previous lab run')
  parser.add_argument(
    '--validate',
    dest='validate',
    action='store_true',
    help=argparse.SUPPRESS)
  return parser

"""
Get lab topology from the snapshot file or run the transformation process
"""
def get_topology(args: argparse.Namespace, cli_args: typing.List[str]) -> Box:
  up_args_parser = up_parse_args(bool(args.snapshot))         # (re)create the correct parser

  if args.snapshot:                                           # If we're using the snapshot file...
    args = up_args_parser.parse_args(cli_args)                # ... and reparse
    log.set_logging_flags(args)                               # ... use these arguments to set logging flags and read the snapshot

    topology = load_snapshot(args,ghosts=False)
    print(f"Using transformed lab topology from snapshot file {args.snapshot}")
  else:                                                       # No snapshot file, use 'netlab create' parser
    log.section_header('Creating','configuration files')
    topology = create.run(cli_args,'up','Create configuration files, start a virtual lab, and configure it',up_args_parser)
    topology = augment.nodes.ghost_buster(topology)

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

Otherwise use 'netlab status' to check the status of labs running on this
machine, or 'netlab down' to shut down the other lab running in this directory.

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

Please use 'netlab status --all' to check the status of labs running on this
machine. You can stop the other lab instance with:

netlab status -i {lab_id} --cleanup

If you think your netlab status file is corrupt, use 'netlab status --reset' to
delete it.
''')
  log.fatal(f'aborting "netlab up" request')

"""
Execute provider probes
"""
def provider_probes(topology: Box) -> None:
  p_provider = topology.provider

  log.section_header('Checking','virtualization provider installation')
  external_commands.run_probes(topology.defaults,p_provider)
  for s_provider in topology[p_provider].providers:
    external_commands.run_probes(topology.defaults,s_provider)

"""
Start lab topology for a single provider
"""
def start_provider_lab(topology: Box, pname: str, sname: typing.Optional[str] = None) -> None:
  p_name   = sname or pname
  p_module = providers.get_provider_module(topology,p_name)

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

  sp_module  = providers.get_provider_module(topology,s_provider)
  s_topology = providers.select_topology(topology,s_provider)         # Create secondary provider subtopology
  filename = sp_data.filename                                         # Get the secondary configuration filename
  print(f"Recreating {filename} configuration file for {s_provider} provider")
  sp_module.create(s_topology,filename)                               # ... and create the new configuration file

"""
Deploy initial configuration
"""
def deploy_initial_config(args: argparse.Namespace, topology: Box) -> None:
  if args.no_config:
    print()
    strings.print_colored_text('[SKIPPED] ','yellow',None)
    print("Initial configuration skipped, run 'netlab initial' to configure the devices")
    return

  lab_status_change(topology,f'deploying initial configuration')
  log.section_header('Deploying','initial device configurations')
  external_commands.deploy_configs("netlab up",args.fast_config)
  lab_status_change(topology,f'initial configuration complete')

  message = get_message(topology,'initial',True)
  if message:
    print(f"\n\n{message}")

"""
Reload saved configurations
"""
def reload_saved_config(args: argparse.Namespace, topology: Box) -> None:
  lab_status_change(topology,f'reloading saved initial configurations')
  log.section_header('Reloading','saved initial device configurations')
  cmd = external_commands.set_ansible_flags(['netlab','config','--reload',args.reload])
  if not external_commands.run_command(cmd):
    log.fatal("netlab config --reload failed, aborting...",'netlab up')
  lab_status_change(topology,f'saved initial configurations reloaded')
  log.status_success()
  print("Saved configurations reloaded")

"""
Check the state of the external tool container
"""
def check_tool_status(tool: str, status: typing.Optional[str], topology: Box) -> bool:
  if status is None:
    return False

  if not re.search('(?i)warning.*platform.*match',status):
    return True

  log.info(f'Platform mismatch between {tool} container image and your hardware, checking tool status')
  time.sleep(0.5)
  c_stat = external_commands.run_command(
              f'docker inspect {topology.name}_{tool}',
              ignore_errors=True,return_stdout=True,check_result=True)

  return bool(c_stat)

"""
Deploy external tools
"""
def start_external_tools(args: argparse.Namespace, topology: Box) -> None:
  if not 'tools' in topology:
    return
  if args.no_tools:
    print()
    strings.print_colored_text('[SKIPPED] ','yellow',None)
    print("External tools not started, start them manually")
    return

  lab_status_change(topology,f'starting external tools')
  log.section_header('Starting','external tools')
  t_count = 0
  t_success = 0
  for tool in topology.tools.keys():
    cmds = external_commands.get_tool_command(tool,'up',topology)
    if cmds is None:
      continue

    t_count += 1
    status = external_commands.execute_tool_commands(cmds,topology)
    if not is_dry_run() and not check_tool_status(tool,status,topology):
      log.error(f'Failed to start {tool}',module='tools',category=Warning,skip_header=True)
      continue
    msg = external_commands.get_tool_message(tool,topology)
    if not is_dry_run():
      t_success += 1
      log.status_success()
      print(f"{tool} tool started")

    if msg:
      print(("DRY_RUN: " if is_dry_run() else "") + msg + "\n")

  lab_status_change(topology,f'{t_success}/{t_count} external tools started')
  if not is_dry_run():
    log.partial_success(t_success,t_count)
    print(f"{t_success}/{t_count} external tools started")

"""
Main "lab start" process
"""
def run_up(cli_args: typing.List[str]) -> None:
  up_args_parser = up_parse_args(False)                       # Try to parse the up-specific arguments
  (args,rest) = up_args_parser.parse_known_args(cli_args)
  if args.reload and args.no_config:
    log.fatal('Cannot combine --reload-config and --no-config')

  set_dry_run(args)
  if not args.snapshot and not is_dry_run():
    check_existing_lab()

  topology = get_topology(args,cli_args)
  if not is_dry_run():
    check_lab_instance(topology)

  if log.QUIET:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "selective"

  external_commands.LOG_COMMANDS = True
  provider_probes(topology)
  if not args.no_config:
    process_config_sw_check(topology)

  p_provider = topology.provider
  p_module = providers.get_provider_module(topology,p_provider)
  providers.mark_providers(topology)
  p_module.call('pre_output_transform',topology)

  providers.validate_images(topology)

  status_start_lab(topology)
  if 'err_conflict' in topology.defaults:
    log.fatal(f'race condition, lab instance already running in {topology.defaults.err_conflict}')

  if not is_dry_run():
    _status.lock_directory()

  log.section_header('Starting',f'{p_provider} nodes')
  start_provider_lab(topology,p_provider)

  for s_provider in topology[p_provider].providers:
    log.section_header('Starting',f'{s_provider} nodes')
    recreate_secondary_config(topology,p_provider,s_provider)
    start_provider_lab(topology,p_provider,s_provider)

  if topology.get('defaults.tc.enable',True):
    providers.execute_tc_commands(topology)

  try:
    if args.reload:
      reload_saved_config(args,topology)
    else:
      deploy_initial_config(args,topology)
  except KeyboardInterrupt:                           # netlab initial already displayed the error message
    sys.exit(1)

  start_external_tools(args,topology)
  lab_status_change(topology,'started')
  if _status.is_directory_locked():                   # If we're using the lock file, touch it after we're done
    _status.lock_directory()                          # .. to have a timestamp of when the lab was started

  log.repeat_warnings('netlab up')

  try:
    stats.update_topo_stats(topology)
  except Exception as ex:
    log.warning(
      text=f'Cannot update usage stats: {str(ex)}',
      module='stats')

  if args.validate:
    if args.no_config:
      log.warning(text='Lab is not configured, skipping the validation phase',module='-')
    else:
      try:
        status = external_commands.run_command('netlab validate',return_exitcode=True)
        if status == 1:
          log.error('Validation failed',log.FatalError,module='netlab validate')
        elif status == 3:
          log.warning(text='Validation generated a warning',module='netlab validate')
      except KeyboardInterrupt:                       # netlab validate displays its own error message
        sys.exit(1)

def run(cli_args: typing.List[str]) -> None:
  try:
    run_up(cli_args)
  except KeyboardInterrupt:
    external_commands.interrupted('netlab up')
