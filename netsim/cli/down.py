#
# netlab down command
#
# * Transform lab topology or read transformed lab topology from snapshot file
# * Stop the lab, including provider-specific pre- and post-stop hooks
# * Clean up the working directory (optional)
#
import argparse
import typing
import textwrap
import os
import sys
from box import Box

from . import external_commands
from . import lab_status_change,get_lab_id,fs_cleanup
from .. import read_topology,common,providers
from ..utils import status,strings
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
    '--force',
    dest='force',
    action='store_true',
    help='Force shutdown or cleanup (use at your own risk)')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')

  return parser.parse_args(args)

def down_cleanup(topology: Box, verbose: bool = False) -> None:
  p_provider = topology.provider
  cleanup_list = topology.defaults.providers[p_provider].cleanup or []

  for s_provider in topology[p_provider].providers:
    cleanup_list.extend(topology.defaults.providers[s_provider].cleanup or [])
    s_filename = topology.defaults.providers[p_provider][s_provider].filename
    if s_filename:
      cleanup_list.append(s_filename)

  cleanup_list.extend(topology.defaults.automation.ansible.cleanup)
  cleanup_list.append('netlab.snapshot.yml')
  fs_cleanup(cleanup_list,verbose)

def stop_provider_lab(topology: Box, pname: str, sname: typing.Optional[str] = None) -> None:
  p_name = sname or pname
  p_topology = providers.select_topology(topology,p_name)
  p_module   = providers._Provider.load(p_name,topology.defaults.providers[p_name])

  exec_command = None
  if sname is not None:
    exec_command = topology.defaults.providers[pname][sname].stop

  p_module.call('pre_stop_lab',p_topology)
  external_commands.stop_lab(topology.defaults,p_name,2,"netlab down",exec_command)
  p_module.call('post_stop_lab',p_topology)

'''
lab_dir_mismatch -- check if the lab instance is running in the current directory
'''
def lab_dir_mismatch(topology: Box) -> bool:
  lab_id = get_lab_id(topology)
  lab_status = status.read_status(topology)       # Find current running instance(s)
  if not lab_id in lab_status:                    # This could be a lab instance from pre-status days
    return False                                  # ... in which case we can shut it down
  if lab_id in lab_status and lab_status[lab_id].dir == os.getcwd():
    return False                                 # Lab instance is known  and this is the correct directory        

  print(f'''
According to the netlab status file, the lab instance '{lab_id}' is running
in directory {lab_status[lab_id].dir}.

You could proceed if you want to clean up the netlab artifacts from this
directory, but you might impact the running lab instance.
''')
  if not strings.confirm('Do you want to proceed?'):
    common.fatal('aborting lab shutdown request')

  return True

'''
Remove the lab instance/directory from the status file
'''
def remove_lab_status(topology: Box) -> None:
  lab_id = get_lab_id(topology)

  status.change_status(
    topology,
    callback = lambda s,t: s.pop(lab_id,None))

def run(cli_args: typing.List[str]) -> None:
  args = down_parse(cli_args)
  if not os.path.isfile(args.snapshot):
    print(f"The topology snapshot file {args.snapshot} does not exist.\n"+
          "Looks like no lab was started from this directory")
    sys.exit(1)

  print(f"Reading transformed lab topology from snapshot file {args.snapshot}")
  topology = read_topology.read_yaml(filename=args.snapshot)
  if topology is None:
    common.fatal('... could not read the lab topology, aborting')
    return

  mismatch = lab_dir_mismatch(topology)

  lab_status_change(topology,f'lab shutdown requested{" in conflicting directory" if mismatch else ""}')
  try:
    provider_probes(topology)
  except:
    if not args.force:
      return

  p_provider = topology.provider
  p_module = providers._Provider.load(p_provider,topology.defaults.providers[p_provider])
  providers.mark_providers(topology)
  p_module.call('pre_output_transform',topology)

  for s_provider in topology[p_provider].providers:
    lab_status_change(topology,f'stopping {s_provider} provider')
    try:
      stop_provider_lab(topology,p_provider,s_provider)
    except:
      if not args.force:
        return
    print()

  try:
    stop_provider_lab(topology,p_provider)
  except:
    if not args.force:
      return

  if args.cleanup:
    external_commands.print_step(3,"Cleanup configuration files",spacing = True)
    down_cleanup(topology,True)

  if not mismatch:
    remove_lab_status(topology)
  status.unlock_directory()
