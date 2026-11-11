"""
SSH utility functions

* Check whether the "sshpass" command is available
"""
import shutil

from ..cli import error_and_exit
from . import log


def check_sshpass(reason: str) -> None:
  """
  Check whether the "sshpass" command is available and abort otherwise

  The 'reason' parameter explains why the caller needs sshpass and is displayed as a hint
  """
  if shutil.which('sshpass'):
    return

  error_and_exit(
    'sshpass command is not installed',
    more_hints=[reason],
    category=log.MissingDependency)
