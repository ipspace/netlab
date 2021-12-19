#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob
import subprocess
import shutil

from box import Box
from pathlib import Path

from .. import common
from .. import read_topology
from . import external_commands

#
# CLI parser for 'netlab config' command
#
def test_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  choices = ( p for p in settings.providers.keys() if 'start' in settings.providers[p] )
  parser = argparse.ArgumentParser(
    prog='netlab test',
    description='Test virtual lab installation')
  parser.add_argument(
    '-w','--work-directory',
    dest='workdir',
    action='store',
    default='test',
    help='Working directory (default: test)')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default=0,
    help='Verbose logging')
  parser.add_argument(
    dest='provider',
    action='store',
    choices=list(choices),
    help='Run tests for the specified provider')

  return parser.parse_args(args)

def copy_topology(args: argparse.Namespace) -> None:
  if args.verbose:
    print("Creating test topology file in %s" % args.workdir)
  os.mkdir(args.workdir)
  os.chdir(args.workdir)
  moddir = Path(__file__).resolve().parent.parent

  src_topo = moddir / "templates/tests" / (args.provider + ".yml")
  try:
    shutil.copy(src_topo,"topology.yml")
  except:
    common.fatal("Cannot copy test topology file %s into %s" % (src_topo,args.workdir))
  if args.verbose:
    print("... done, moving on\n")

def create_configs() -> None:
  external_commands.print_step(2,"creating configuration files")
  if not external_commands.run_command(["netlab","create"],True):
    common.fatal("netlab create failed, aborting...","netlab test")

def cleanup_working_directory(args: argparse.Namespace) -> None:
  if args.verbose:
    print("\nCleaning up -- removing %s and its contents" % args.workdir)
  os.chdir("..")
  try:
    shutil.rmtree(args.workdir)
  except:
    print("... cannot clean up working directory, trying to run 'sudo rm -fr'")
    try:
      subprocess.run(["sudo","rm","-fr",args.workdir],check=True)
      print("... that worked ;)")
    except:
      print("... rm -fr failed, please clean up %s manually" % args.workdir)
      return

  if args.verbose:
    print("... done, test completed\n")

def run(cli_args: typing.List[str]) -> None:
  settings = read_topology.read_yaml('package:topology-defaults.yml')
  if not cli_args:
    common.fatal("Specify the virtualization environment to test or use -h to get help","test")
    return

  if not settings:
    common.fatal("Cannot read the global defaults","test")
    return

  args = test_parse(cli_args,settings)
  if os.path.exists(args.workdir):
    common.fatal("Directory %s already exists, aborting" % args.workdir,"test")

  if args.verbose:
    common.set_verbose(args.verbose)
  external_commands.run_probes(settings,args.provider,1)
  copy_topology(args)
  create_configs()
  if not external_commands.run_command('netlab up'):
    common.fatal('netlab up failed, aborting','test')
  elif not external_commands.run_command('netlab down'):
    common.fatal('netlab down failed','test')
#  external_commands.start_lab(settings,args.provider,3)
#  external_commands.deploy_configs(4)
#  external_commands.stop_lab(settings,args.provider,5)
  cleanup_working_directory(args)
