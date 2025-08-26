#
# netlab config command
#
# Deploy custom configuration template to network devices
#
import argparse
import csv
import os
import sysconfig
import typing
from pathlib import Path

from box import Box

from ..utils import log, read, strings
from ..utils.files import get_moddir
from . import error_and_exit, external_commands, set_dry_run


#
# CLI parser for 'netlab install' command
#
def install_parse(args: typing.List[str], setup: Box) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog='netlab install',
    description='Install additional software',
    epilog='Run "netlab install" with no arguments to get install script descriptions')
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
    '--all',
    dest='all',
    action='store_true',
    help='Run all installation scripts')
  parser.add_argument(
    '--dry-run',
    dest='dry_run',
    action='store_true',
    help=argparse.SUPPRESS)
  parser.add_argument(
    dest='script',
    action='store',
    nargs="*",
    help='Run the specified installation script')

  return parser.parse_args(args)

"""
read_config_setup: Read the installation configuration file and add information
from /etc/os-release file (if it exists)
"""
def read_config_setup() -> Box:
  cf_name = 'package:install/install.yml'
  setup = read.read_yaml(filename=cf_name)
  if setup is None or not setup:
    log.fatal(f'Cannot read the installation configuration file {cf_name}')
  
  os_release = Path('/etc/os-release')
  if not os_release.exists():
    log.info(f"The {os_release} file does not exist. I have no idea what operating system you're using")
    setup.distro.ID = "unknown"
  else:
    try:
      with open(os_release) as stream:
        setup.distro = dict(csv.reader(stream, delimiter="="))
    except Exception as ex:
      error_and_exit(f'Cannot read {str(os_release)}: {str(ex)}')
  return setup

"""
Adjust installation configuration:

* Update 'env' dictionary from topology variables
"""
def adjust_setup(setup: Box, topology: Box, args: argparse.Namespace) -> None:
  for k,v in setup.env.items():
    if v in topology.defaults:
      os.environ[k] = topology.defaults[v]
      if args.verbose:
        print(f'ENV: {k}={os.environ[k]}')

"""
check_crazy_pip3: deals with crazy pip3 that thinks installing Python packages in
local directory will break its sanity
"""
def check_crazy_pip3(args: argparse.Namespace) -> None:
  syspath = sysconfig.get_path("stdlib")
  if os.path.exists(f'{syspath}/EXTERNALLY-MANAGED'):
    if not args.yes:
      print()
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
    print()
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
set_quiet_flags: based on CLI flags, set flags for PIP/APT
"""
def set_quiet_flags(args: argparse.Namespace) -> None:
  os.environ['FLAG_PIP'] = ''
  os.environ['FLAG_APT'] = ''
  os.environ['FLAG_QUIET'] = ''

  if args.verbose and args.quiet:
    error_and_exit(
      'Cannot specify --quiet and --verbose at the same time',
      more_hints='Take a break and make up your mind')

  if args.verbose:
    os.environ['FLAG_APT'] = '-V'
    os.environ['FLAG_PIP'] = '-v'

  if args.quiet:
    os.environ['FLAG_APT'] = '-qq'
    os.environ['FLAG_QUIET'] = '-qq'
    os.environ['FLAG_PIP'] = '-qq'

  if args.yes:
    os.environ['FLAG_YES'] = 'Y'

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
Select the most appropriate distribution settings for the current script
"""
def select_distro(script: str, setup: Box, args: argparse.Namespace) -> None:
  s_data = setup.scripts[script]
  distro = None
  if setup.distro.ID in s_data.distro:                # Perfect match
    distro = setup.distro.ID
  else:                                               # Otherwise iterate over target distros and    
    for t_distro in s_data.distro:                    # ... compare them to ID_LIKE
      if t_distro in setup.distro.ID_LIKE:
        distro = t_distro                             # ... the first match is considered the best
        break

  if distro is None:
    error_and_exit(
      f"We don't have {script} installation script for your Linux distribution ({setup.distro.ID})",
      more_hints=f'This script is only available for {",".join(s_data.distro)}')
  else:
    os.environ['DISTRIBUTION'] = distro
    if args.verbose:
      log.info(f"Running installation script for {distro}")

"""
Checks whether it's OK to run the specified installation script:

* Is 'apt-get' command used and available?
* Is 'pip3' command used, available, and are we using virtual environment
"""
def check_script(script: str, setup: Box, args: argparse.Namespace) -> None:
  s_data = setup.scripts[script]
  if 'distro' in s_data:
    select_distro(script,setup,args)
  if 'apt' in s_data.uses:
    if not external_commands.has_command('apt-get'):
      error_and_exit(
        'This script uses apt-get command that is not available on your system',
        more_hints='Most netlab installation scripts work on Ubuntu and Debian)',
        category=log.IncorrectType)
    os.environ['FLAG_APT'] = os.environ.get('FLAG_APT','') + " -o DPkg::Lock::Timeout=30"

  if 'pip' not in s_data.uses:
    return

  if not external_commands.has_command('pip3'):
    error_and_exit(
      'This script uses pip3 command that is not available on your system',
      more_hints="Install pip3 (for example, with 'sudo apt-get install python-pip3')",
      category=log.IncorrectType)

  if os.environ.get('VIRTUAL_ENV',None):
    log.info(
      "You're running netlab in a Python virtual environment",
      more_hints='Python libraries will be installed in the same environment')
    print()
    os.environ['SUDO'] = ''
    return

  check_crazy_pip3(args)

"""
Display what the installation script will do and ask for user confirmation
"""
def script_confirm(script: str,setup: Box, args: argparse.Namespace) -> None:
  if args.quiet:
    return

  s_data = setup.scripts[script]
  if s_data.intro:
    print()
    log.info(s_data.intro,more_hints = setup.shared.intro or None)
    print()

  if not args.yes and not strings.confirm("Are you sure you want to proceed"):
    error_and_exit('User aborted the installation process',category=Warning)

"""
Installation script has completed
"""
def script_completed(script: str,setup: Box, args: argparse.Namespace) -> None:
  if args.quiet:
    return

  s_data = setup.scripts[script]
  log.section_header('Done   ',f'Completed {s_data.description} installation')
  if s_data.epilog:
    print()
    log.info(s_data.epilog)

def display_usage(setup: Box) -> None:
  t_usage = []
  for s_name,s_data in setup.scripts.items():
    t_usage.append([ s_name, s_data.get('description','') ])
  strings.print_table(['Script','Installs'],t_usage,inter_row_line=False)

def run(cli_args: typing.List[str]) -> None:
  setup = read_config_setup()

  if not cli_args:
    display_usage(setup)
    return

  args = install_parse(cli_args,setup)
  topology = read.system_defaults()
  adjust_setup(setup,topology,args)

  for script in args.script:
    if script not in setup.scripts:
      error_and_exit(
        f'Unknown installation script {script}',
        more_hints='Run "netlab install" to display the available installation scripts')

  set_quiet_flags(args)
  set_dry_run(args)
  set_sudo_flag()
  install_path = f'{get_moddir()}/install'
  os.environ['PATH'] = install_path + ":" + os.environ['PATH']
  for script in setup.scripts.keys():
    if script not in args.script and not args.all:
      continue
    script_path = f'{install_path}/{script}.sh'
    if not os.path.exists(script_path):
      log.fatal("Installation script {script} does not exist")

    log.section_header('Install',setup.scripts[script].description)
    script_confirm(script,setup,args)
    check_script(script,setup,args)
    if not args.quiet:
      log.section_header('Running',f'{script} installation script')

    try:
      if not external_commands.run_command(['bash',script_path],ignore_errors=True):
        print()
        log.fatal(f"Installation script {script}.sh failed, exiting")
      else:
        script_completed(script,setup,args)

    except KeyboardInterrupt:
      print()
      log.fatal('User aborted the installation request')
    except Exception:
      log.fatal('Python exception: {ex}')
