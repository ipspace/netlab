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
from pathlib import Path

from ..utils import log

#
# CLI parser for 'netlab install' command
#
def install_parse(args: typing.List[str]) -> argparse.Namespace:
  moddir = Path(__file__).resolve().parent.parent
  choices = map(
    lambda x: Path(x).stem,
    glob.glob(str(moddir / "install/*sh")))

  parser = argparse.ArgumentParser(
    prog='netlab install',
    description='Install additional software')
  parser.add_argument(
    '-v','--verbose',
    dest='verbose',
    action='store_true',
    help='Verbose logging')
  parser.add_argument(
    '-q','--quiet',
    dest='quiet',
    action='store_true',
    help='Be as quiet as possible')
  parser.add_argument(
    '-y','--yes',
    dest='yes',
    action='store_true',
    help='Run the script without prompting for a confirmation')
  parser.add_argument(
    dest='script',
    action='store',
    choices=list(choices),
    nargs="*",
    help='Run the specified installation script')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  if not cli_args:
    log.fatal("Specify an installation script to run or use -h to get help","install")

  args = install_parse(cli_args)

  moddir = Path(__file__).resolve().parent.parent
  env = { key:value for (key,value) in os.environ.items() }
  if args.verbose:
    env['FLAG_APT'] = '-V'
    env['FLAG_PIP'] = '-v'

  if args.quiet:
    env['FLAG_APT'] = '-qq'
    env['FLAG_QUIET'] = '-qq'
    env['FLAG_PIP'] = '-qq'

  if args.yes:
    env['FLAG_YES'] = 'Y'

  for script in args.script:
    script_path = str(moddir / "install" / (script+".sh"))
    if args.verbose:
      print("Running installation script: %s" % script_path)

    try:
      subprocess.run(
        ['bash',script_path],
        check=True,
        env=env)
    except:
      print("\nInstallation script %s.sh failed, exiting..." % script)
      return
