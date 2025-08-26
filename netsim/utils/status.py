#
# Common routines used to implement lab status and locking commands
#

import os
import sys
import typing

from box import Box
from filelock import FileLock

from ..data import get_empty_box
from ..utils import log, strings

'''
get_status_filename -- get the name of the netlab status file
'''
def get_status_filename(topology: Box) -> str:
  status_file = topology.defaults.lab_status_file or '~/.netlab/status.yaml'
  return os.path.expanduser(status_file)

'''
Get lab ID for multilab deployments (moved here to be used by more than just CLI routines)
'''
def get_lab_id(topology: Box) -> str:
  return topology.get('defaults.multilab.id','default') or 'default'    # id could be set to {} due to tool f-string evals

'''
change_status -- change the status of a lab

* Lock the lab status file
* Read the YAML document in the lab status file
* Call a callback function to change the status
* Write the modified YAML document
* Unlock the lab status file
'''
def change_status(topology: Box, callback: typing.Callable[[Box,Box], None]) -> None:
  status_file = get_status_filename(topology)               # Get status file name from topology defaults
  lock_file   = f'{status_file}.lock'                       # Associated lock file

  try:
    status_dir = os.path.dirname(status_file)
    if not os.path.exists(status_dir):
      os.makedirs(status_dir)
  except:
    log.fatal(f'Cannot create lab status directory {status_dir}')

  try:                                                      # Try to lock the status file          
    lock = FileLock(lock_file, timeout=3)
    lock.acquire()
    if os.path.exists(status_file):                       # If the status file exists, read it
      try:
        status = Box().from_yaml(filename=status_file,default_box=True,box_dots=True)
      except:
        log.fatal(f'Cannot read lab status file {status_file}')
    else:                                                 # Otherwise, create an empty status
      status = get_empty_box()

    callback(status,topology)                               # Change the lab status
    if log.debug_active('status'):
      print(f'Lab status: {status}')
    with open(status_file, 'w') as f:                       # Write the modified status          
      f.write(strings.get_yaml_string(status))
  except:
    log.fatal(f'Cannot lock lab status file {lock_file}\n... {sys.exc_info()[0]}')
  finally:
    lock.release()

def read_status(topology: Box) -> Box:
  status_file = get_status_filename(topology)               # Get status file name from topology defaults
  if not os.path.exists(status_file):
    return get_empty_box()
  
  try:
    return Box().from_yaml(filename=status_file,default_box=True,box_dots=True)
  except:
    log.fatal(f'Cannot read lab status file {status_file}')
    return get_empty_box()

'''
Remove the lab instance/directory from the status file
'''
def remove_lab_status(topology: Box) -> None:
  lab_id = get_lab_id(topology)

  change_status(
    topology,
    callback = lambda s,t: s.pop(lab_id,None))

'''
lock_directory -- create netlab.lock file in current directory to prevent 
                  overwriting provider configuration files or Ansible inventory
'''
lock_file: typing.Final[str] = 'netlab.lock'

def lock_directory() -> None:
  global lock_file

  if os.path.exists(lock_file):
    os.utime(lock_file,None)
  else:
    with open(lock_file, 'w') as f:
      f.write('netlab lock file, do not remove')

'''
unlock_directory -- remove netlab.lock file in current directory
'''
def unlock_directory() -> None:
  global lock_file
  if os.path.exists(lock_file):
    os.remove(lock_file)

'''
is_locked -- check if netlab.lock file exists in current directory
'''
def is_directory_locked() -> bool:
  global lock_file
  return os.path.exists(lock_file)

'''
lock_timestamp -- return mtime of the lock file or None if it does not exist
'''
def lock_timestamp() -> typing.Optional[typing.Union[int,float]]:
  global lock_file
  if os.path.exists(lock_file):
    return os.stat(lock_file).st_mtime
  else:
    return None
