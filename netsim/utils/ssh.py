"""
SSH utility functions

* Check whether the "sshpass" command is available
"""
import shutil

from . import log


def check_sshpass(reason: str, module: str = 'netlab') -> None:
  """
  Check whether the "sshpass" command is available and abort otherwise

  The 'reason' parameter explains why the caller needs sshpass and is displayed as a hint
  """
  if shutil.which('sshpass'):
    return

  log.error(
    'sshpass command is not installed',
    category=log.MissingDependency,
    module=module,
    more_hints=[reason],
    skip_header=True,
    exit_on_error=True)
