#
# Common Ansible interface commands
#

import json
import os
import subprocess
import sys
import typing
from pathlib import Path

from box import Box

from ..data import get_box
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
          "We tested netlab core with Ansible version 13.x but some rarely-used devices might",
          "not work properly. You might want to downgrade Ansible to version 11.10 or lower." ],
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

def playbook(name: str, args: typing.List[str], abort_on_error: bool = True) -> bool:
  pbname = find_playbook(name)
  if not pbname:
    log.fatal("Cannot find Ansible playbook %s, aborting" % name)

  if log.VERBOSE:
    print("Running Ansible playbook %s" % pbname)

  cmd = ['ansible-playbook',pbname]
  cmd.extend(args)

  OK = external_commands.run_command(cmd,ignore_errors=not abort_on_error and not log.VERBOSE)
  if not OK and abort_on_error:
    log.fatal(f"Executing Ansible playbook {pbname} failed")

  return OK is True

"""
Create the extra vars structure that will be passed to Ansible playbook to modify
the search paths. We could just change the Ansible playbooks, but this keeps some
level of compatibility with older code (and an escape strategy ;).
"""
def ansible_extra_vars(topology: Box, reload: bool = False, extra_vars: typing.Optional[dict] = None) -> Box:
  cfg_sfx = '.cfg' if reload else ''

  if extra_vars is None:
    extra_vars = {}
  ev = get_box(extra_vars)
  ev.node_files = str(Path("./node_files").resolve().absolute())

  ev.paths_t_files.files = "{{ config_module }}" + cfg_sfx    # Take only module file from node_files
  ev.paths_custom.files = "{{ custom_config }}" + cfg_sfx     # And rendered custom config from node_files
  for p in ['templates','custom']:                            # Change the search paths to node_files
    ev[f'paths_{p}'].dirs = "{{ node_files }}/{{ inventory_hostname }}"

  # Retain the custom configuration task name(s) and directories
  ev.paths_custom.tasks = topology.defaults.paths.custom.tasks
  ev.paths_custom.task_dirs = topology.defaults.paths.custom.dirs
  return ev
