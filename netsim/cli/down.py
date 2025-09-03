#
# netlab down command
#
# * Transform lab topology or read transformed lab topology from snapshot file
# * Stop the lab, including provider-specific pre- and post-stop hooks
# * Clean up the working directory (optional)
#
import argparse
import os
import sys
import typing

from box import Box

from .. import providers
from ..utils import log, status, strings
from . import (
  external_commands,
  fs_cleanup,
  is_dry_run,
  lab_status_change,
  load_snapshot,
  parser_lab_location,
  set_dry_run,
)
from .up import provider_probes


#
# CLI parser for 'netlab down' command
#
def down_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab down",
    description='Destroy the virtual lab')

  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default = 0,
    help='Verbose logging (where applicable)')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Remove all configuration files created by netlab create')
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help='Print the commands that would be executed, but do not execute them')
  parser.add_argument(
    '--force',
    dest='force',
    action='count', default = 0,
    help='Force shutdown or cleanup (use at your own risk)')
  parser_lab_location(parser,instance=True,snapshot=True,action='shut down')

  return parser.parse_args(args)

#
# Cleanup common configuration files
#
def down_cleanup(topology: Box, verbose: bool = False) -> None:
  p_provider = topology.provider
  cleanup_list = topology.defaults.providers[p_provider].cleanup or []

  for s_provider in topology[p_provider].providers:
    cleanup_list.extend(topology.defaults.providers[s_provider].cleanup or [])
    s_filename = topology.defaults.providers[p_provider][s_provider].filename
    if s_filename:
      cleanup_list.append(s_filename)

  cleanup_list.extend(topology.defaults.automation.ansible.cleanup)
  for v in topology.get('_cleanup',{}).values():
    cleanup_list += v if isinstance(v,list) else [ v ]

  cleanup_list.append('netlab.snapshot.yml')
  cleanup_list.append('netlab.snapshot.pickle')
  fs_cleanup(cleanup_list,verbose)

#
# Cleanup tool configuration directories and other tool-related stuff
#
def tool_cleanup(topology: Box, verbose: bool = False) -> None:
  for tool in list(topology.tools.keys()):
    cmds = external_commands.get_tool_command(tool,'cleanup',topology,verbose=False) or []
    cmds.append(f'rm -fr {tool}')
    external_commands.execute_tool_commands(cmds,topology)
    if not is_dry_run():
      print(f"... cleaned up {tool} data")

#
# Stop the provider-specific workloads
#
def stop_provider_lab(
      topology: Box,
      pname: str,
      sname: typing.Optional[str] = None) -> None:
  p_name = sname or pname
  p_topology = providers.select_topology(topology,p_name)
  p_module   = providers.get_provider_module(topology,p_name)

  exec_command = None
  if sname is not None:
    exec_command = topology.defaults.providers[pname][sname].stop

  p_module.call('pre_stop_lab',p_topology)
  external_commands.stop_lab(topology.defaults,p_name,"netlab down",exec_command)
  p_module.call('post_stop_lab',p_topology)

'''
lab_dir_mismatch -- check if the lab instance is running in the current directory
'''
def lab_dir_mismatch(topology: Box, args: argparse.Namespace) -> bool:
  lab_id = status.get_lab_id(topology)
  lab_status = status.read_status(topology)       # Find current running instance(s)
  if not lab_id in lab_status:                    # This could be a lab instance from pre-status days
    return False                                  # ... in which case we can shut it down
  if lab_id in lab_status and lab_status[lab_id].dir == os.getcwd():
    return False                                 # Lab instance is known  and this is the correct directory        

  if args.force >= 2:
    return True

  print(f'''
According to the netlab status file, the lab instance '{lab_id}' is running
in directory {lab_status[lab_id].dir}.

You could proceed if you want to clean up the netlab artifacts from this
directory, but you might impact the running lab instance.
''')
  if not strings.confirm('Do you want to proceed?'):
    log.fatal('aborting lab shutdown request')

  return True

"""
Stop external tools
"""
def stop_external_tools(args: argparse.Namespace, topology: Box) -> None:
  lab_status_change(topology,f'stopping external tools')
  for tool in list(topology.tools.keys()):
    cmds = external_commands.get_tool_command(tool,'down',topology)
    if cmds is None:
      continue
    external_commands.execute_tool_commands(cmds,topology)
    if not is_dry_run():
      print(f"... {tool} tool stopped")

  lab_status_change(topology,f'external tools stopped')

def stop_all(topology: Box, args: argparse.Namespace) -> None:
  if 'tools' in topology:
    log.section_header('Stopping','external tools','yellow')
    stop_external_tools(args,topology)

  p_provider = topology.provider
  p_module = providers.get_provider_module(topology,p_provider)
  providers.mark_providers(topology)
  p_module.call('pre_output_transform',topology)

  for s_provider in topology[p_provider].providers:
    lab_status_change(topology,f'stopping {s_provider} provider')
    try:
      log.section_header('Stopping',f'{s_provider} nodes','yellow')
      stop_provider_lab(topology,p_provider,s_provider)
    except:
      if not args.force:
        sys.exit(1)
    print()

  try:
    lab_status_change(topology,f'stopping {p_provider} provider')
    log.section_header('Stopping',f'{p_provider} nodes','yellow')
    stop_provider_lab(topology,p_provider)
  except:
    if not args.force:
      sys.exit(1)

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  set_dry_run(args)
  log.set_logging_flags(args)

  topology = load_snapshot(args,ghosts=False)
  mismatch = lab_dir_mismatch(topology,args)

  probes_OK = True
  external_commands.LOG_COMMANDS = True
  lab_status_change(topology,f'lab shutdown requested{" in conflicting directory" if mismatch else ""}')
  try:
    provider_probes(topology)
  except:
    probes_OK = False
    if not args.force:
      return

  if probes_OK:
    stop_all(topology,args)

  if args.cleanup:
    if 'tools' in topology:
      log.section_header('Cleanup',f'tool configuration','yellow')
      tool_cleanup(topology,True)

    log.section_header('Cleanup',f'configuration files','yellow')
    down_cleanup(topology,True)

  if not mismatch:
    status.remove_lab_status(topology)

  if not is_dry_run():
    status.unlock_directory()
