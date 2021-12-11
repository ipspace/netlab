#
# Common Ansible interface commands
#

import typing
import subprocess
import sys
import os
import json
from pathlib import Path

from .. import common

try:
  from importlib import resources
except ImportError:
  import importlib_resources as resources # type: ignore

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
      common.fatal('Cannot parse JSON data returned by ansible-inventory','inventory')
    return None

  except:
    try:
      subprocess.run(['ansible-inventory','-h'],capture_output=True,check=True)
    except:
      common.fatal('Cannot execute ansible-inventory','inventory')
    common.fatal('Cannot get Ansible inventory data for %s with ansible-inventory. Is the host name correct?' % name,'inventory')

  return None

def playbook(name: str, args: typing.List[str]) -> None:
  pbname = find_playbook(name)
  if not pbname:
    common.fatal("Cannot find Ansible playbook %s, aborting" % name)
    return

  if common.VERBOSE:
    print("Running Ansible playbook %s" % pbname)

  cmd = ['ansible-playbook',pbname]
  cmd.extend(args)

  try:
    subprocess.check_call(cmd)
  except:
    common.fatal("Ansible playbook failed")
