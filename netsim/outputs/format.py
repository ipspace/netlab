#
# This is just a dummy output module that was replaced by the new 'report'
# output module. We kept the old module (pointing to the new one) in case
# someone already used it in their workflow.
#
import typing
from .report import REPORT

class FORMAT(REPORT):
  DESCRIPTION :typing.Any = None
