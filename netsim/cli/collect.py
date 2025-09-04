#
# netlab collect command
#
# Collect device configurations
#
import argparse
import os
import subprocess
import typing

from ..utils import log
from . import ansible, external_commands, fs_cleanup, parser_lab_location


#
# CLI parser for 'netlab collect' command
#
def collect_parse(args: typing.List[str]) -> typing.Tuple[argparse.Namespace, typing.List[str]]:
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
    '--suffix',
    dest='suffix',
    action='store',
    default='cfg',
    help='Configure file(s) suffix (default: cfg)')
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
  parser_lab_location(parser,instance=True,action='collect configuration from')

  return parser.parse_known_args(args)

def get_tarball_file(tarball: str) -> str:
  if not '.tar' in tarball:
    tarball = tarball + '.tar.gz'
  return tarball

def run(cli_args: typing.List[str]) -> None:
  run_dir = os.getcwd()
  (args,rest) = collect_parse(cli_args)
  log.set_logging_flags(args)

  fs_cleanup([ args.output ])
  try:
    os.mkdir(args.output)
  except Exception as ex:
    log.fatal(f"Cannot create output directory {args.output}: {ex}")

  print(f"cwd: {os.getcwd()} output: {args.output}")
  if args.verbose:
    rest = ['-v'] + rest

  rest = ['-e','target='+args.output ] + rest

  if args.suffix:
    rest += ['-e','suffix='+args.suffix]

  if args.tar and not args.quiet:
    external_commands.print_step(1,"Collecting device configurations")

  if args.verbose:
    print("Ansible playbook args: %s" % rest)

  if args.quiet:
    os.environ["ANSIBLE_STDOUT_CALLBACK"] = "dense"

  ansible.playbook('collect-configs.ansible',rest)

  if args.tar:
    if os.getcwd() != run_dir:
      log.status_green('CHANGED','')
      print(f'Changing current directory back to {run_dir}')
      os.chdir(run_dir)

    tarball = get_tarball_file(args.tar)
    if not args.quiet:
      external_commands.print_step(2,f"Creating tarball {args.tar}",spacing = True)
    try:
      subprocess.check_call(['tar','cfz' if args.quiet else 'cvfz',tarball,args.output])
    except Exception as ex:
      log.fatal(f"Cannot start tar: {ex}")

    if args.cleanup:
      if not args.quiet:
        external_commands.print_step(3,"Cleanup config directory",spacing = True)
      fs_cleanup([ args.output ],args.verbose)
      print("... done")

  log.repeat_warnings('netlab collect')
