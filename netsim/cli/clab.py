#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import string
import pathlib
import glob
import subprocess
import shutil

from box import Box

from ..utils import files as _files, log, strings, read as _read
from . import external_commands
from . import collect
from . import fs_cleanup

def tarball_parse(args: typing.List[str], settings: Box) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab clab tarball',
    description='Create a ready-to-use tarball containing containerlab configuration file and startup configs')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='count',
    default=0,
    help='Verbose logging')
  parser.add_argument(
    '-q','--quiet',
    dest='quiet',
    action='store_true',
    help='Run Ansible playbook and tar with minimum output')
  parser.add_argument(
    '--config',
    dest='output',
    action='store',
    nargs='?',
    default='config',
    help='Startup configuration directory (default: config)')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Clean up config directory and modified configuration file after creating tarball')
  parser.add_argument(
    dest='tarball',
    action='store',
    type=argparse.FileType('w'),
    help='Destination tarball (.tar.gz will be added if needed)')
  return parser.parse_args(args)

def find_config_file(n: str, cfglist: typing.List[str]) -> typing.Optional[str]:
  for fname in cfglist:
    if fname == n:
      return fname
    if fname.find(n+'.') == 0:
      return fname

  return None

def clab_config_adjust(infile: str, outfile: str, configs: str) -> None:
  clab = _read.read_yaml(infile)
  if not clab:
    log.fatal("Cannot read clab.yml configuration file, aborting")

  clab_yml = strings.get_yaml_string(clab)
  if not ('topology' in clab and 'nodes' in clab.topology):
    log.fatal(f'Containerlab configuration file {infile} is weird: cannot find topology.nodes dictionary')

  try:
    cfglist = os.listdir(configs)
  except Exception as ex:
    log.fatal(f'Cannot read the contents of {configs} directory: {ex}')

  for n in list(clab.topology.nodes.keys()):
    cfgfile = find_config_file(n,cfglist)
    if cfgfile:
      cfgfile = f"{configs}/{cfgfile}"
      print(f"Found config file for {n}: {cfgfile}")
      clab.topology.nodes[n]['startup-config'] = cfgfile

  final_clab_yml = strings.get_yaml_string(clab) 
  if final_clab_yml == clab_yml:
    log.fatal(f'No relevant configuration files were found in {configs} directory, aborting')

  _files.create_file_from_text(outfile,final_clab_yml)

def clab_tarball(cli_args: typing.List[str], settings: Box) -> None:
  args = tarball_parse(cli_args,settings)

  if not os.path.exists('clab.yml'):
    log.fatal('Containerlab configuration file clab.yml not found, aborting...')

  external_commands.print_step(1,"Collecting device configurations")
  os.environ["ANSIBLE_STDOUT_CALLBACK"] = "dense"
  collect.run(['-o',args.output])

  external_commands.print_step(2,"Adjusting containerlab configuration file",spacing = True)
  clab_config_adjust(infile='clab.yml',outfile='clab.config.yml',configs=args.output)

  external_commands.print_step(3,"Creating tarball",spacing = True)
  tarball = collect.get_tarball_file(args.tarball.name)

  try:
    subprocess.check_call(['tar','cfz' if args.quiet else 'cvfz',tarball,'clab.config.yml',args.output])
  except Exception as ex:
    log.fatal(f"Cannot start tar: {ex}")

  if args.cleanup:
    external_commands.print_step(4,"Cleanup",spacing = True)
    fs_cleanup([ args.output,'clab.config.yml' ])
    print("... done")

def clab_usage() -> None:
  print("Usage: netlab clab tarball --help")

def run(cli_args: typing.List[str]) -> None:
  settings = _read.read_yaml('package:topology-defaults.yml')
  if not cli_args:
    clab_usage()
    return

  if not settings:
    log.fatal("Cannot read the system defaults","clab")

  if cli_args[0] == 'tarball':
    clab_tarball(cli_args[1:],settings)
  else:
    clab_usage()
