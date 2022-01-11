#!/usr/bin/env python3
#
# Main CLI entry point
#

import sys
import importlib
import argparse
from box import Box

from . import usage
from .. import augment, common, read_topology

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
    parser.add_argument('--debug', dest='debug', action='store_true',
                    help='Debugging (might not execute external commands)')

  return parser

def topology_parse_args() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Common topology arguments',add_help=False)
  parser.add_argument('--defaults', dest='defaults', action='store', default='topology-defaults.yml',
                  help='Local topology defaults file')
  parser.add_argument('-d','--device', dest='device', action='store', help='Default device type')
  parser.add_argument('-p','--provider', dest='provider', action='store',help='Override virtualization provider')
  parser.add_argument('-s','--set',dest='settings', action='append',help='Additional parameters added to topology file')
  return parser

# Common topology loader (used by create and down)

def load_topology(args: argparse.Namespace) -> Box:
  common.set_logging_flags(args)
  topology = read_topology.load(args.topology.name,args.defaults,"package:topology-defaults.yml")

  if args.settings or args.device or args.provider:
    topology.nodes = augment.nodes.create_node_dict(topology.nodes)
    read_topology.add_cli_args(topology,args)

  common.exit_on_error()
  return topology

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
      print( f"Error importing .{cmd},{__name__}: {ex}" )
      pass

  if mod and hasattr(mod,'run'):
    mod.run(sys.argv[arg_start:])   # type: ignore
    return

  print("Invalid CLI command: %s\n\nUse 'netlab usage' to get the list of valid commands" % cmd)
  sys.exit(1)
