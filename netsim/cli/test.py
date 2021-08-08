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
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    dest='provider',
    action='store',
    choices=list(choices),
    help='Run tests for the specified provider')

  return parser.parse_args(args)

def print_step(n: int, txt: str, spacing: typing.Optional[bool] = False) -> None:
  if spacing:
    print()
  print("Step %d: %s" % (n,txt))
  print("=" * 60)

def test_probe(p : str) -> bool:
  args = p.split(" ")
  try:
    result = subprocess.run(args,capture_output=True,check=True,text=True)
    return result.stdout != ""
  except:
    return False

def run_probes(settings: Box, args: argparse.Namespace) -> None:
  if args.verbose:
    print("Checking virtualization provider installation")
  for p in settings.providers[args.provider].probe:
    if args.verbose:
      print(".. executing: %s" % p)
    if not test_probe(p):
      common.fatal("%s failed, aborting" % p)
  if args.verbose:
    print(".. all tests succeeded, moving on\n")

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

def create_configs(args: argparse.Namespace) -> None:
  print_step(1,"creating configuration files")
  try:
    subprocess.run(["netlab","create"],check=True)
  except:
    common.fatal("netlab create failed, aborting...","test")

def start_lab(settings: Box, args: argparse.Namespace) -> None:
  print_step(2,"starting the lab",True)
  cmd = settings.providers[args.provider].start
  try:
    subprocess.run(cmd.split(" "),check=True)
  except:
    common.fatal("%s failed, aborting..." % cmd,"test")

def deploy_configs(args: argparse.Namespace) -> None:
  print_step(3,"deploying initial device configurations")
  try:
    subprocess.run(["netlab","initial"],check=True)
  except:
    common.fatal("netlab initial failed, aborting...","test")

def stop_lab(settings: Box, args: argparse.Namespace) -> None:
  print_step(4,"stopping the lab",True)
  cmd = settings.providers[args.provider].stop
  try:
    subprocess.run(cmd.split(" "),check=True)
  except:
    common.fatal("%s failed, aborting..." % cmd,"test")

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

  args = test_parse(cli_args,settings)
  if os.path.exists(args.workdir):
    common.fatal("Directory %s already exists, aborting" % args.workdir,"test")

  run_probes(settings,args)
  copy_topology(args)
  create_configs(args)
  start_lab(settings,args)
  deploy_configs(args)
  stop_lab(settings,args)
  cleanup_working_directory(args)
