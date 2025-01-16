#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import typing
import argparse
import os
import glob
import sysconfig
import subprocess
from pathlib import Path

from ..utils import log,strings
from . import external_commands

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
    '-u','--user',
    dest='user',
    action='store_true',
    help='Install Python libraries into user .local directory')
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help=argparse.SUPPRESS)
  parser.add_argument(
    dest='script',
    action='store',
    choices=list(choices),
    nargs="*",
    help='Run the specified installation script')

  return parser.parse_args(args)

"""
check_crazy_pip3: deals with crazy pip3 that thinks installing Python packages in
local directory will break its sanity
"""
def check_crazy_pip3(args: argparse.Namespace) -> None:
  syspath = sysconfig.get_path("stdlib")
  if os.path.exists(f'{syspath}/EXTERNALLY-MANAGED'):
    if not args.yes:
      log.info(
        "Your Linux distribution includes a scared version of Python",
        more_hints=[
          "This version of Python thinks you should only install stuff in a virtual environment.",
          "You could abort the installation process, create a virtual environment and retry.",
          "OTOH, if you're using netlab on a dedicated server or VM, you probably don't care"])
      if not strings.confirm('Do you want to install Python libraries without a virtual environment',blank_line=True):
        log.fatal('Aborting. Create and activate a virtual environment and retry.')

    os.environ['FLAG_PIP'] = os.environ['FLAG_PIP'] + ' --break-system-packages'

  if not args.user and not args.yes:
    log.info(
      "We will install Python libraries into system directories",
      more_hints=[
        "You should install Python into system directories if you want multiple users to",
        "use netlab on this server/VM, otherwise it might be a better idea to start the",
        "netlab install command with the --user option. However, if you're installing",
        "netlab on a dedicated server or VM, you probably don't care."])
    if not strings.confirm('Do you want to install Python libraries into system directories',blank_line=True):
      log.fatal("Aborting. Restart 'netlab install' with the --user option")

  if args.user:
    os.environ['SUDO'] = ""
    os.environ['FLAG_PIP']  = os.environ['FLAG_PIP'] + ' --user'
    os.environ['FLAG_USER'] = 'Y'

"""
set_sudo_flag: figures out whether we have 'sudo' installed and whether the user
is a root user if there's no sudo.
"""
def set_sudo_flag() -> None:
  os.environ['SUDO'] = ""
  os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
  os.environ['NEEDRESTART_MODE'] = 'a'

  if os.getuid() == 0:
    return

  if external_commands.has_command('sudo'):
    os.environ['SUDO'] = "sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a"
    return

  log.warning(
    text="sudo command is not available and you're not root. The installation will most likely fail",
    module='install')

  if strings.confirm('Do you want to continue',blank_line=True):
    return

  log.fatal('Installation aborted')

"""
Checks whether it's OK to run the specified installation script:

* Is 'apt-get' command used and available?
* Is 'pip3' command used, available, and are we using virtual environment
"""
def check_script(path: str, args: argparse.Namespace) -> None:
  script = Path(path)
  cmds = script.read_text()

  if ' apt-get ' in cmds:
    if not external_commands.has_command('apt-get'):
      log.error(
        'This script uses apt-get command that is not available on your system',
        more_hints='Most netlab installation scripts work on Ubuntu (and probably on Debian)',
        category=log.IncorrectType)
      log.fatal('Aborting installation request')

  if ' pip3 ' not in cmds:
    return

  if not external_commands.has_command('pip3'):
    log.error(
      'This script uses pip3 command that is not available on your system',
      more_hints="Install pip3 (for example, with 'sudo apt-get install python-pip3')",
      category=log.IncorrectType)
    log.fatal('Aborting installation request')

  if os.environ.get('VIRTUAL_ENV',None):
    log.info(
      "You're running netlab in a Python virtual environment",
      more_hints='Python libraries will be installed in the same environment')
    print()
    os.environ['SUDO'] = ''
    return

  check_crazy_pip3(args)

def run(cli_args: typing.List[str]) -> None:
  if not cli_args:
    log.fatal("Specify an installation script to run or use -h to get help","install")

  args = install_parse(cli_args)

  moddir = Path(__file__).resolve().parent.parent
  os.environ['FLAG_PIP'] = ''

  if args.verbose:
    os.environ['FLAG_APT'] = '-V'
    os.environ['FLAG_PIP'] = '-v'

  if args.quiet:
    os.environ['FLAG_APT'] = '-qq'
    os.environ['FLAG_QUIET'] = '-qq'
    os.environ['FLAG_PIP'] = '-qq'

  if args.yes:
    os.environ['FLAG_YES'] = 'Y'

  set_sudo_flag()
  for script in args.script:
    script_path = str(moddir / "install" / (script+".sh"))
    if not os.path.exists(script_path):
      log.fatal("Installation script {script} does not exist")

    check_script(script_path,args)

    if args.verbose:
      print("Running installation script: %s" % script_path)

    try:
      if not external_commands.run_command(['bash',script_path],ignore_errors=True):
        print()
        log.fatal(f"Installation script {script}.sh failed, exiting")
    except KeyboardInterrupt as ex:
      print()
      log.fatal('User aborted the installation request')
    except Exception as ex:
      log.fatal('Python exception: {ex}')
