#
# Import common routines into a single namespace for backward-compatibility reasons
#

from .data.global_vars import get_topology

from .utils.log import LOGGING, VERBOSE, DEBUG, QUIET, RAISE_ON_ERROR, WARNING
from .utils.log import MissingValue, IncorrectAttr, IncorrectValue, IncorrectType, FatalError, ErrorAbort
from .utils.log import fatal, error, exit_on_error, set_logging_flags, set_flag, print_verbose, debug_active
from .utils.strings import extra_data_printout,format_structured_dict,print_structured_dict,get_yaml_string
