#!/usr/bin/env python3
#
# Main CLI entry point
#

import sys
import importlib
import argparse
import os
import shutil
import typing

from box import Box

from . import usage
from .. import augment, common, read_topology
from .. import __version__

def common_parse_args(debugging: bool = False) -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Common argument parsing',add_help=False)
  parser.add_argument('--log', dest='logging', action='store_true',
                  help='Enable basic logging')
  parser.add_argument('-q','--quiet', dest='quiet', action='store_true',
                  help='Report only major errors')
  parser.add_argument('-v','--verbose', dest='verbose', action='count', default = 0,
                  help='Verbose logging (add multiple flags for increased verbosity)')
  parser.add_argument('--warning', dest='warning', action='store_true',help=argparse.SUPPRESS)
  parser.add_argument('--raise_on_error', dest='raise_on_error', action='store_true',help=argparse.SUPPRESS)
  if debugging:
    parser.add_argument('--debug', dest='debug', action='store',nargs='*',
                    choices=[
                      'all','addr','cli','links','libvirt','modules','plugin','template',
                      'vlan','vrf','quirks','validate','addressing','groups','quirks'
                    ],
                    help=argparse.SUPPRESS)

  return parser

def topology_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Common topology arguments',add_help=False)
  parser.add_argument('--defaults', dest='defaults', action='store',
                  help='Local topology defaults file')
  parser.add_argument('-d','--device', dest='device', action='store', help='Default device type')
  parser.add_argument('-p','--provider', dest='provider', action='store',help='Override virtualization provider')
  parser.add_argument('--plugin',dest='plugin',action='append',help='Additional plugin(s)')
  parser.add_argument('-s','--set',dest='settings', action='append',help='Additional parameters added to topology file')
  return parser

#
# Common file/directory cleanup routine, used by collect/clab/down
#

def fs_cleanup(filelist: typing.List[str], verbose: bool = False) -> None:
  for fname in filelist:
    if os.path.isdir(fname):
      if verbose:
        print(f"... removing directory tree {fname}")
      try:
        shutil.rmtree(fname)
      except Exception as ex:
        common.fatal(f"Cannot clean up directory {fname}: {ex}")
    elif os.path.exists(fname):
      if verbose:
        print(f"... removing {fname}")
      try:
        os.remove(fname)
      except Exception as ex:
        common.fatal(f"Cannot remove {fname}: {ex}")

# Common topology loader (used by create and down)

def load_topology(args: typing.Union[argparse.Namespace,Box]) -> Box:
  common.set_logging_flags(args)
  topology = read_topology.load(args.topology.name,args.defaults,"package:topology-defaults.yml")

  if args.settings or args.device or args.provider or args.plugin:
    topology.nodes = augment.nodes.create_node_dict(topology.nodes)
    read_topology.add_cli_args(topology,args)

  common.exit_on_error()
  return topology

# Snapshot-or-topology loader (used by down)

def load_snapshot_or_topology(args: typing.Union[argparse.Namespace,Box]) -> typing.Optional[Box]:
  common.set_logging_flags(args)
  if args.device or args.provider or args.settings:     # If we have -d, -p or -s flag
    if not args.topology:                               # ... then the user wants to use the topology file
      args.topology = 'topology.yml'                    # ... so let's set the default value if needed

  if args.topology:
    topology = load_topology(args)
    augment.main.transform(topology)
    common.exit_on_error()
    return topology
  else:
    args.snapshot = args.snapshot or 'netlab.snapshot.yml'
    return read_topology.read_yaml(filename=args.snapshot)

# get_message: get action-specific message from topology file
#

def get_message(topology: Box, action: str, default_message: bool = False) -> typing.Optional[str]:
  if not 'message' in topology:
    return None

  if isinstance(topology.message,str):                      # We have a single message
    return topology.message if default_message else None    # If the action is OK with getting the default message return it

  if not isinstance(topology.message,Box):                  # Otherwise we should be dealing with a dict
    common.fatal('topology message should be a string or a dict')
    return None

  return topology.message.get(action,None)                  # Return action-specific message if it exists

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

def lab_commands() -> None:
  if len(sys.argv) < 2:
    usage.run([])
    sys.exit()

  arg_start = 2
  mod = None
  cmd = sys.argv[1]

  if cmd == 'debug':
    arg_start = 3
    mod = importlib.import_module("."+sys.argv[2],__name__)
  elif quick_commands.get(cmd,None):
    quick_commands[cmd](sys.argv[arg_start:])
    return
  else:
    try:
      mod = importlib.import_module("."+cmd,__name__)
    except Exception as ex:
      if 'dev' in __version__:
        print( f"Error importing .{cmd},{__name__}: {ex}" )
  
  if mod:
    if hasattr(mod,'run'):
      mod.run(sys.argv[arg_start:])   # type: ignore
      return

  print("Invalid netlab command '%s'\nUse 'netlab usage' to get the list of valid commands" % cmd)
  sys.exit(1)
