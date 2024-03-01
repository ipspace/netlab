#!/usr/bin/env python3
#
# Main CLI entry point
#

import sys
import importlib
import datetime
import argparse
import os
import shutil
import typing

from box import Box

from . import usage
from .. import augment
from .. import __version__
from ..utils import status as _status, log, read as _read
from ..data import global_vars

DRY_RUN: bool = False
NETLAB_SCRIPT: str = ''

def parser_add_debug(parser: argparse.ArgumentParser) -> None:
  parser.add_argument('--debug', dest='debug', action='store',nargs='*',
                  choices=sorted([
                    'all','addr','cli','links','libvirt','clab','modules','plugin','template',
                    'vlan','vrf','quirks','validate','addressing','groups','status',
                    'external','defaults']),
                  help=argparse.SUPPRESS)
  parser.add_argument('--test', dest='test', action='store',nargs='*',
                  choices=['errors'],
                  help=argparse.SUPPRESS)

# Some CLI utilities might use the 'verbose' flag without other common arguments
#
def parser_add_verbose(parser: argparse.ArgumentParser) -> None:
  parser.add_argument('-v','--verbose', dest='verbose', action='count', default = 0,
                  help='Verbose logging (add multiple flags for increased verbosity)')
  parser.add_argument('-q','--quiet', dest='quiet', action='store_true',
                  help='Report only major errors')

def common_parse_args(debugging: bool = False) -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Common argument parsing',add_help=False)
  parser.add_argument('--log', dest='logging', action='store_true',
                  help='Enable basic logging')
  parser.add_argument('--warning', dest='warning', action='store_true',help=argparse.SUPPRESS)
  parser.add_argument('--raise_on_error', dest='raise_on_error', action='store_true',help=argparse.SUPPRESS)
  parser_add_verbose(parser)
  if debugging:
    parser_add_debug(parser)

  return parser

def topology_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Common topology arguments',add_help=False)
  parser.add_argument('--defaults', dest='defaults', action='store',nargs='*',
                  help='Local topology defaults file')
  parser.add_argument('-d','--device', dest='device', action='store', help='Default device type')
  parser.add_argument('-p','--provider', dest='provider', action='store',help='Override virtualization provider')
  parser.add_argument('--plugin',dest='plugin',action='append',help='Additional plugin(s)')
  parser.add_argument('-s','--set',dest='settings', action='append',help='Additional parameters added to topology file')
  return parser

def set_dry_run(args: argparse.Namespace) -> None:
  global DRY_RUN

  if 'dry_run' in args:
    DRY_RUN = args.dry_run
  else:
    DRY_RUN = False

def is_dry_run() -> bool:
  global DRY_RUN
  return DRY_RUN

#
# Common file/directory cleanup routine, used by collect/clab/down
#

def fs_cleanup(filelist: typing.List[str], verbose: bool = False) -> None:
  global DRY_RUN
  for fname in filelist:
    if os.path.isdir(fname):
      if DRY_RUN:
        print(f"DRY RUN: removing directory tree {fname}")
        continue
      if verbose:
        print(f"... removing directory tree {fname}")
      try:
        shutil.rmtree(fname)
      except Exception as ex:
        log.fatal(f"Cannot clean up directory {fname}: {ex}")
    elif os.path.exists(fname):
      if DRY_RUN:
        print(f"DRY RUN: removing {fname}")
        continue
      if verbose:
        print(f"... removing {fname}")
      try:
        os.remove(fname)
      except Exception as ex:
        log.fatal(f"Cannot remove {fname}: {ex}")

# Common topology loader (used by create and down)

def load_topology(args: typing.Union[argparse.Namespace,Box]) -> Box:
  log.set_logging_flags(args)
  relative_name = 'test' in args and args.test and 'errors' in args.test
  topology = _read.load(args.topology.name,args.defaults,relative_topo_name=relative_name)

  if args.settings or args.device or args.provider or args.plugin:
    topology.nodes = augment.nodes.create_node_dict(topology.nodes)
    _read.add_cli_args(topology,args)

  log.exit_on_error()
  return topology

# Snapshot-or-topology loader (used by down)

def load_snapshot(args: typing.Union[argparse.Namespace,Box]) -> Box:
  if not os.path.isfile(args.snapshot):
    print(f"The topology snapshot file {args.snapshot} does not exist.\n"+
          "Looks like no lab was started from this directory")
    sys.exit(1)

  topology = _read.read_yaml(filename=args.snapshot)
  if topology is None:
    print(f"Cannot read the topology snapshot file {args.snapshot}")
    sys.exit(1)

  global_vars.init(topology)
  return topology

def load_snapshot_or_topology(args: typing.Union[argparse.Namespace,Box]) -> typing.Optional[Box]:
  log.set_logging_flags(args)
  if args.device or args.provider or args.settings:     # If we have -d, -p or -s flag
    if not args.topology:                               # ... then the user wants to use the topology file
      args.topology = 'topology.yml'                    # ... so let's set the default value if needed

  if args.topology:
    topology = load_topology(args)
    augment.main.transform(topology)
    log.exit_on_error()
    return topology
  else:
    args.snapshot = args.snapshot or 'netlab.snapshot.yml'
    return _read.read_yaml(filename=args.snapshot)

# get_message: get action-specific message from topology file
#

def get_message(topology: Box, action: str, default_message: bool = False) -> typing.Optional[str]:
  global DRY_RUN
  if not 'message' in topology or DRY_RUN:
    return None

  if isinstance(topology.message,str):                      # We have a single message
    return topology.message if default_message else None    # If the action is OK with getting the default message return it

  if not isinstance(topology.message,Box):                  # Otherwise we should be dealing with a dict
    log.fatal('topology message should be a string or a dict',module='topology',header=True)

  return topology.message.get(action,None)                  # Return action-specific message if it exists

"""
lab_status_update -- generic lab status callback

* Get the lab ID (or default)
* Map lab ID into current directory
* Merge status dictionary or perform status-specific callback
"""

def lab_status_update(
      topology: Box,
      status: Box,
      update: typing.Optional[dict] = None,
      cb: typing.Optional[typing.Callable] = None) -> None:

  if DRY_RUN:                                               # Don't update status if we're in dry-run mode 
    return
  lab_id = _status.get_lab_id(topology)                     # Get the lab ID (or default)
  if not lab_id in status:
    status[lab_id].dir = os.getcwd()                        # Map lab ID into current directory
  if not 'providers' in status[lab_id]:                     # Initialize provider list
    status[lab_id].providers = []

  if update is not None:                                    # Update lab status from a dictionary
    status[lab_id] = status[lab_id] + update
    if 'status' in update:                                  # Append change in lab status to log        
      if not 'log' in status[lab_id]:                       # Create empty log if needed
        status[lab_id].log = []

      # Append status change to log if it's not a duplicate of the last entry
      # This is to avoid excessive log entries when the status is updated multiple times
      # in a row (e.g. when a lab is being created)
      #
      if not status[lab_id].log or not f': {update["status"]}' in status[lab_id].log[-1]:
        timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
        status[lab_id].log.append(f'{timestamp}: {update["status"]}')

  if cb is not None:                                        # If needed, perform status-specific callback        
    cb(status[lab_id])

"""
lab_status_change -- change current lab status
"""
def lab_status_change(topology: Box, new_status: str) -> None:
  global DRY_RUN
  if DRY_RUN:                                              # Don't update status if we're in dry-run mode 
    return

  _status.change_status(
    topology,
    callback = lambda s,t: 
      lab_status_update(t,s,
        update = { 'status': new_status }))

#
# Main command dispatcher
#
# The command to execute is the first CLI argument. We try to load a module with the same name
# and if the module load fails for whatever reason we generate an error and exit.
#
# However, the module load could fail due to coding errors within the module (not because the module
# does not exist), in which case the 'debug' command becomes useful - it loads the required module
# without the exception handling, resulting in a nice error printout.
#
# After we have the module that we hope will execute the desired command, we check whether it has
# a 'run' function, and if it does, we call it with the remaining arguments.
#

quick_commands = {
  'alias': lambda x: usage.print_usage('alias.txt')
}

def lab_commands(script: str) -> None:
  global NETLAB_SCRIPT
  NETLAB_SCRIPT = script

  if len(sys.argv) < 2:
    usage.run([])
    sys.exit()

  arg_start = 2
  mod = None
  cmd = sys.argv[1]

  if cmd in ['-h','--help']:
    cmd = 'usage'

  if cmd == 'debug':
    arg_start = 3
    cmd = sys.argv[2]
    mod = importlib.import_module("."+sys.argv[2],__name__)
  elif quick_commands.get(cmd,None):
    quick_commands[cmd](sys.argv[arg_start:])
    return

  mod_path = os.path.dirname(__file__) + f"/{cmd}.py"
  if not os.path.isfile(mod_path):
    print("Unknown netlab command '%s'\nUse 'netlab usage' to get the list of valid commands" % cmd)
    sys.exit(1)

  try:
    mod = importlib.import_module("."+cmd,__name__)
  except Exception as ex:
    log.fatal(f"Error importing {__name__}.{cmd}: {ex}")

  if mod:
    if hasattr(mod,'run'):
      mod.run(sys.argv[arg_start:])   # type: ignore
      return
    else:
      log.fatal(f"Module {__name__}.{cmd} does not have a valid entry point")
  else:
    log.fatal(f'Could not import module {__name__}.{cmd}')

  sys.exit(1)
