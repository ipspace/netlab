#
# Cisco IOS-XE quirks
#
from box import Box

from . import _Quirks
from .iol import IOSXE as _IOSXE

class CSR(_IOSXE):
  pass
