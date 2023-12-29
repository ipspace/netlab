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

from ..utils import log,read as _read, files as _files
from . import external_commands

#
# CLI parser for 'netlab config' command
#
def test_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  c_path  = _files.get_traversable_path('package:templates/tests')   # Directory containing test scenarios
  c_list  = _files.get_globbed_files(c_path,'*.yml')                  # Find all test scenarios
  choices = [ Path(fn).stem for fn in c_list ]

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
    help='Run tests for the specified provider/environment')

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
    log.fatal("Cannot copy test topology file %s into %s" % (src_topo,args.workdir))
  if args.verbose:
    print("... done, moving on\n")

def cleanup_force() -> None:
  print('''
==============================================================================
The test has failed. We will try to clean up the test directory and remove it,
but there's no guarantee that the cleanup process will succeed, in which case
please remove the test directory manually.

You might want to copy the error messages generated during the test before
proceeding. The cleanup process will start once you press RETURN.
==============================================================================
''')
  input('Press RETURN to continue -> ')
  log.section_header('Executing','netlab down --cleanup --force','bright_cyan')
  external_commands.run_command('netlab down --cleanup --force')

def cleanup_working_directory(args: argparse.Namespace, force_cleanup: bool) -> None:
  if force_cleanup:
    cleanup_force()
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
  settings = _read.read_yaml('package:topology-defaults.yml')
  if not cli_args:
    log.fatal("Specify the virtualization environment to test or use -h to get help","test")

  if not settings:
    log.fatal("Cannot read the global defaults","test")

  args = test_parse(cli_args,settings)
  if os.path.exists(args.workdir):
    log.fatal("Directory %s already exists, aborting" % args.workdir,"test")

  if args.verbose:
    log.set_logging_flags(args)

  log.section_header('Checking',f'{args.provider} installation')
  external_commands.run_probes(settings,args.provider)

  copy_topology(args)
  force_cleanup = False
  log.section_header('Executing','netlab up','bright_cyan')
  if not external_commands.run_command('netlab up'):
    log.error('netlab up failed, aborting',log.FatalError,'test')
    force_cleanup = True
  else:
    log.section_header('Executing','netlab down','bright_cyan')
    if not external_commands.run_command('netlab down'):
      log.error('netlab down failed',log.FatalError,'test')
      force_cleanup = True

  if not force_cleanup:
    log.section_header('Success',f'{args.provider} is installed and working correctly')

  cleanup_working_directory(args,force_cleanup)
