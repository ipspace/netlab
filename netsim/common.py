#
# Common routines for create-topology script
#
import sys
import typing
import box

if box.__version__ < '7.0':
  print("FATAL ERROR: python-box version 7.0 or higher required, use 'pip3 install --upgrade python-box' to install")
  sys.exit(1)

from .data.global_vars import get_topology

from .utils.log import LOGGING, VERBOSE, DEBUG, QUIET, RAISE_ON_ERROR, WARNING
from .utils.log import MissingValue, IncorrectAttr, IncorrectValue, IncorrectType, FatalError, ErrorAbort
from .utils.log import fatal, error, exit_on_error, set_logging_flags, set_flag, print_verbose, debug_active
from .utils.strings import extra_data_printout,format_structured_dict,print_structured_dict,get_yaml_string

AF_LIST = ['ipv4','ipv6']
BGP_SESSIONS = ['ibgp','ebgp']

