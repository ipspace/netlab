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

_VERSION_MISMATCH: typing.Optional[bool] = None   # Cached result of the Ansible version check

"""
Check whether the installed Ansible version might be incompatible with netlab. The check is
performed only once; the result is cached and returned on subsequent calls. The warning is
displayed only when a playbook fails (see 'playbook' function)
"""
def check_version() -> bool:
  global _VERSION_MISMATCH
  if _VERSION_MISMATCH is not None:
    return _VERSION_MISMATCH

  _VERSION_MISMATCH = False
  try:
    import ansible  # type: ignore
    if ansible.__version__ >= '2.19':           # Ansible core 2.19 contains significant templating changes
      _VERSION_MISMATCH = True
  except Exception as ex:
    log.warning(text="Cannot determine Ansible version",module='ansible',more_data=str(ex))

  return _VERSION_MISMATCH

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
  except Exception as ex:
    try:                                          # Check whether we can execute ansible-inventory at all
      subprocess.run(['ansible-inventory','-h'],capture_output=True,check=True)
    except Exception as h_ex:
      log.fatal('Cannot execute ansible-inventory command','inventory',more_data=str(h_ex))

    log.fatal(
      f'Cannot get Ansible inventory data for {name} with ansible-inventory',
      'inventory',
      more_data=(getattr(ex,'stderr','') or str(ex)).strip(),
      more_hints='Is the host name correct?')

  try:
    return json.loads(result.stdout)
  except Exception as ex:
    log.fatal('Cannot parse JSON data returned by ansible-inventory','inventory',more_data=str(ex))

def playbook(name: str, args: typing.List[str], abort_on_error: bool = True) -> bool:
  pbname = find_playbook(name)
  if not pbname:
    log.fatal("Cannot find Ansible playbook %s, aborting" % name)

  if log.VERBOSE:
    print("Running Ansible playbook %s" % pbname)

  check_version()
  cmd = ['ansible-playbook',pbname]
  cmd.extend(args)

  OK = external_commands.run_command(cmd,ignore_errors=not abort_on_error and not log.VERBOSE)
  if not OK and _VERSION_MISMATCH:              # Remind the user the playbook failure might be caused by Ansible version
    log.warning(
      text=f"Ansible playbook {name} failed, possibly due to the unsupported Ansible version",
      more_hints = [
        "Ansible core version 2.19 introduced breaking changes in templates and playbooks.",
        "We tested netlab core with Ansible version 14.x but some rarely-used devices might",
        "not work properly. Consider downgrading Ansible to version 11.10 or lower." ],
      module='ansible',
      flag='ver12')

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

  if reload:                                                  # Extra variables needed to make reload work
    ev.netlab_ansible_skip_module = []                        # Do not skip modules in Ansible playbooks (there's no other mechanism)

  ev.paths_t_files.files = "{{ config_module }}" + cfg_sfx    # Take only module file from node_files
  ev.paths_custom.files = "{{ custom_config }}" + cfg_sfx     # And rendered custom config from node_files
  for p in ['templates','custom']:                            # Change the search paths to node_files
    ev[f'paths_{p}'].dirs = "{{ node_files }}/{{ inventory_hostname }}"

  # Retain the custom configuration task name(s) and directories
  ev.paths_custom.tasks = topology.defaults.paths.custom.tasks
  ev.paths_custom.task_dirs = topology.defaults.paths.custom.dirs
  return ev
