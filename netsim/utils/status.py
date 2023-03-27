#
# Common routines used to implement lab status commands
#

import typing
import os
from box import Box
from filelock import Timeout, FileLock

from ..common import fatal, get_yaml_string,debug_active
from ..data import get_empty_box

'''
get_status_filename -- get the name of the netlab status file
'''
def get_status_filename(topology: Box) -> str:
  status_file = topology.defaults.lab_status_file or '~/.netlab/status.yaml'
  return os.path.expanduser(status_file)

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
    fatal(f'Cannot create lab status directory {status_dir}')

  try:                                                      # Try to lock the status file          
    lock = FileLock(lock_file, timeout=3)
    with lock:
      if os.path.exists(status_file):                       # If the status file exists, read it
        try:
          status = Box().from_yaml(filename=status_file,default_box=True,box_dots=True)
        except:
          fatal(f'Cannot read lab status file {status_file}')
      else:                                                 # Otherwise, create an empty status
        status = get_empty_box()

    callback(status,topology)                               # Change the lab status
    if debug_active('status'):
      print(f'Lab status: {status}')
    with open(status_file, 'w') as f:                       # Write the modified status          
      f.write(get_yaml_string(status))
  except:
    fatal(f'Cannot lock lab status file {lock_file}')

def read_status(topology: Box) -> Box:
  status_file = get_status_filename(topology)               # Get status file name from topology defaults
  if not os.path.exists(status_file):
    return get_empty_box()
  
  try:
    return Box().from_yaml(filename=status_file,default_box=True,box_dots=True)
  except:
    fatal(f'Cannot read lab status file {status_file}')
    return get_empty_box()
