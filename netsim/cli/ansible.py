#
# Common Ansible interface commands
#

import json
import os
import subprocess
import sys
import typing
from pathlib import Path

from ..utils import log
from . import external_commands


def check_version(fatal: bool = False) -> None:
  try:
    import ansible  # type: ignore
    if ansible.__version__ >= '2.19':           # Ansible core 2.19 contains significant templating changes
      log.warning(
        text="You're using Ansible version 12.x or higher; netlab might not work correctly",
        more_hints = [
          "Ansible core version 2.19 introduced breaking changes in templates and playbooks",
          "We tested netlab core with Ansible version 12.x but not every device template",
          "You might want to downgrade Ansible to version 11.10 or lower.",
          "Use 'netlab install ansible' on Ubuntu to do that",
          "Finally, please open a GitHub issue if you experience errors/crashes"],
        module='ansible',
        flag='ver12',
        category=log.FatalError if fatal else Warning)
  except Exception as ex:
    log.warning(text=f"Cannot determine Ansible version: {str(ex)}",module='ansible')

def find_playbook(name: str) -> typing.Union[str,None]:
  cwd = Path(os.getcwd()).resolve()
  scriptdir = Path(sys.argv[0]).resolve().parent
  moddir = Path(__file__).resolve().parent.parent

  for dir in [cwd,cwd / 'ansible',scriptdir / 'ansible',moddir / 'ansible']:
    if os.path.isfile(dir / name):
      return str(dir / name)

  return None

def inventory(name: str) -> typing.Optional[dict]:
  try:
    result = subprocess.run(['ansible-inventory','--host',name],capture_output=True,check=True,text=True)
    try:
      return json.loads(result.stdout)
    except:
      log.fatal('Cannot parse JSON data returned by ansible-inventory','inventory')

  except:
    try:
      subprocess.run(['ansible-inventory','-h'],capture_output=True,check=True)
    except Exception as ex:
      log.fatal(f'Cannot execute ansible-inventory command\n  {ex}','inventory')

    log.fatal('Cannot get Ansible inventory data for %s with ansible-inventory. Is the host name correct?' % name,'inventory')

def playbook(name: str, args: typing.List[str]) -> None:
  pbname = find_playbook(name)
  if not pbname:
    log.fatal("Cannot find Ansible playbook %s, aborting" % name)

  if log.VERBOSE:
    print("Running Ansible playbook %s" % pbname)

  cmd = ['ansible-playbook',pbname]
  cmd.extend(args)

  OK = external_commands.run_command(cmd)
  if not OK:
    log.fatal(f"Executing Ansible playbook {pbname} failed")
