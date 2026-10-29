#
# netlab initial -- implement standard device readiness checks
#

import threading

from box import Box

from ....augment import devices as a_devices
from ....utils import log
from ... import error_and_exit, external_commands

PRINT_LOCK = threading.Lock()

def get_int_var_value(n_data: Box, var: str, def_val: int, defaults: Box) -> int:
  """
  Get a group variable (if it's an int) or return a default value
  """
  result = a_devices.get_node_group_var(n_data,var,defaults)
  return result if isinstance(result,int) else def_val

def set_timeouts(n_data: Box, defaults: Box) -> Box:
  """
  Set the node._ready delay/retries/wait parameters from netlab group variables
  """
  r_data = n_data._ready
  r_data.retries = get_int_var_value(n_data,'netlab_check_retries',20,defaults)
  r_data.delay   = get_int_var_value(n_data,'netlab_check_delay',5,defaults)
  r_data.wait    = r_data.retries * r_data.delay
  return r_data

def check_sshpass() -> None:
  """
  Check whether the "sshpass" command is available and abort otherwise
  """
  if not external_commands.has_command('sshpass'):
    error_and_exit(
      'sshpass command is not installed',
      more_hints=['netlab initial needs "sshpass" to check SSH readiness of lab devices'],
      category=log.MissingDependency)
