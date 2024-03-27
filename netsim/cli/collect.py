#
# netlab collect command
#
# Collect device configurations
#
import typing
import os
import argparse
import shutil
import subprocess

from . import common_parse_args,fs_cleanup
from . import ansible
from . import external_commands
from ..utils import log

#
# CLI parser for 'netlab collect' command
#
def initial_config_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
  parser = argparse.ArgumentParser(
    prog="netlab collect",
    description='Collect device configurations',
    epilog='All other arguments are passed directly to ansible-playbook')

  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    '-q','--quiet',
    dest='quiet',
    action='store_true',
    help='Run Ansible playbook and tar with minimum output')
  parser.add_argument(
    '-o','--output',
    dest='output',
    action='store',
    nargs='?',
    default='config',
    help='Output directory (default: config)')
  parser.add_argument(
    '--tar',
    dest='tar',
    action='store',
    help='Create configuration tarball')
  parser.add_argument(
    '--cleanup',
    dest='cleanup',
    action='store_true',
    help='Clean up config directory and modified configuration file after creating tarball')
  return parser.parse_known_args(args)

def get_tarball_file(tarball: str) -> str:
  if not '.tar' in tarball:
    tarball = tarball + '.tar.gz'
  return tarball

def run(cli_args: typing.List[str]) -> None:
  (args,rest) = initial_config_parse(cli_args)
  log.set_logging_flags(args)

  fs_cleanup([ args.output ])
  try:
    os.mkdir(args.output)
  except Exception as ex:
    log.fatal(f"Cannot create output directory {args.output}: {ex}")

  if args.verbose:
    rest = ['-v'] + rest

  rest = ['-e','target='+args.output ] + rest

  if args.tar and not args.quiet:
    external_commands.print_step(1,"Collecting device configurations")

  if args.verbose:
    print("Ansible playbook args: %s" % rest)

  if args.quiet:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "dense"

  ansible.playbook('collect-configs.ansible',rest)

  if args.tar:
    tarball = get_tarball_file(args.tar)
    if not args.quiet:
      external_commands.print_step(2,"Creating tarball",spacing = True)
    try:
      subprocess.check_call(['tar','cfz' if args.quiet else 'cvfz',tarball,args.output])
    except Exception as ex:
      log.fatal(f"Cannot start tar: {ex}")

    if args.cleanup:
      if not args.quiet:
        external_commands.print_step(3,"Cleanup config directory",spacing = True)
      fs_cleanup([ args.output ],args.verbose)
      print("... done")
