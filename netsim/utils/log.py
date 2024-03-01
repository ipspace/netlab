#
# Common routines for create-topology script
#
import sys
import os
import typing
import warnings
import typing
import argparse
from box import Box
from ..data import types as _types
from . import strings

import rich.table

LOGGING : bool = False
VERBOSE : int = 0
DEBUG : typing.Optional[typing.List[str]] = None
QUIET : bool = False

RAISE_ON_ERROR : bool = False
WARNING : bool = False

AF_LIST = ['ipv4','ipv6']
BGP_SESSIONS = ['ibgp','ebgp']

_ERROR_LOG: list = []
_WARNING_LOG: list = []

err_class_map = {                       # Map error classes into short error codes
  'MissingDependency':  'DEPEND',
  'MissingValue':       'MISSING',
  'IncorrectValue':     'VALUE',
  'IncorrectAttr':      'ATTR',
  'IncorrectType':      'TYPE',
  'FatalError':         'FATAL',
  'UserWarning':        'WRONG',
  'Warning':            'WARNING'
}

err_color_map = {
  'FATAL': 'red',
  'WARNING': 'magenta'
}

class MissingDependency(Warning):
  pass

class MissingValue(Warning):
  pass

class IncorrectValue(Warning):
  pass

class IncorrectAttr(Warning):
  pass

class IncorrectType(Warning):
  pass

class FatalError(Warning):
  pass

class ErrorAbort(Exception):
  pass

# Try to print 'Errors encountered while processing _filename_' header
#

_error_header_printed: bool = False

"""
Print "errors found in _topologyname_" error header
"""
def print_error_header() -> None:
  global _error_header_printed
  if _error_header_printed:                     # Header already printed, get out
    return
  
  try:
    from ..data import global_vars
    topology = global_vars.get_topology()       # Get a pointer to topology
    if not topology:
      return

    if topology.input:                          # If we know where we got the topology from, print the error message
      toponame = os.path.basename(topology.input[0])
      if strings.rich_err_color:                # Error is going to terminal with color capabilities
        strings.print_colored_text(strings.pad_err_code('ERRORS'),'red',stderr=True)
        print(f'Errors found in {toponame}',file=sys.stderr)
      else:                                     # Plain old teletype (or file), print error message
        print(f'Errors encountered while processing {toponame}',file=sys.stderr)
      _error_header_printed = True
  except:
    pass

"""
Print the final error message and abort
"""
def fatal(text: str, module: str = 'netlab', header: bool = False) -> typing.NoReturn:
  global _ERROR_LOG

  err_line = f'Fatal error in {module}: {text}'
  _ERROR_LOG.extend(err_line.split("\n"))

  if RAISE_ON_ERROR:                              # CI flag: raise exception instead of aborting
    raise ErrorAbort(text)
  else:
    if WARNING:                                   # CI flag: raise a warning
      warnings.warn_explicit(text,FatalError,filename=module,lineno=len(_ERROR_LOG))
    else:
      if header:
        print_error_header()
      if strings.rich_err_color:                  # Color-capable terminal
        strings.print_colored_text(strings.pad_err_code('FATAL'),'red',stderr=True)
        if module != 'netlab':
          print(f'{module}: ',end='',file=sys.stderr)
        print(text,file=sys.stderr)
      else:                                       # ... or teletype/file
        print(err_line,file=sys.stderr)
    sys.exit(1)

"""
Generic hint-processing function:

* Calculate terminal width
* If needed, wrap hint string into lines
* Cleanup hint list (some callers might be lazy and pass empty hints)
* Append hints to error log (needed for CI test cases), then print them to
  terminal or file
"""
def print_more_hints(
      h_list: typing.Union[list,str],   # Hint split into lines
      h_name: str='HINT',               # Hint header
      h_color: str='green',             # Color of hint header
      cleanup: bool=True) -> None:      # Remove empty lines from hint lines?

  if isinstance(h_list,str):
    h_width = min(strings.rich_err_width,100)
    if strings.rich_err_color:
      h_width = h_width - 10

    h_list = strings.wrap_text_into_lines(h_list,width=h_width)

  if cleanup:
    h_list = [ line for line in h_list if line ]
  if not h_list:
    return

  global _ERROR_LOG
  h_first = True
  for line in h_list:
    _ERROR_LOG.append(f"... {line}")                        # Convention: hints in traditional output are prefaced with ...
    if strings.rich_err_color:
      if h_first:                                           # First hint line on color-capable TTY: print hint header
        strings.print_colored_text(strings.pad_err_code(h_name),h_color,stderr=True)
        print(line,file=sys.stderr)
        h_first = False
      else:
        print(" "*10+line,file=sys.stderr)                  # Otherwise print another line indented to align with the previous one
    else:
      print(f"... {line}",file=sys.stderr)                  # Teletype/file, just print the line

"""
Display an error message, including error category, calling module and optional hints
"""

def error(
      text: str,                                                    # Error text
      category: typing.Type[Warning] = UserWarning,                 # Category (must be one of the classes defined above)
      module: str = 'topology',                                     # Module generating the error
      hint: typing.Optional[str] = None,                            # Pointer to a static hint
      more_hints: typing.Optional[typing.Union[str,list]] = None,   # More hints or extra data
      more_data: typing.Optional[typing.Union[str,list]] = None) -> None:

  global _ERROR_LOG,err_class_map,_WARNING_LOG,QUIET,err_color_map
  err_name = category.__name__
  err_line = f'{err_name} in {module}: {text}' if module else f'{err_name}: {text}'

  if category is Warning:
    if QUIET:
      return
    _WARNING_LOG.extend(f'{module}: {text}'.split("\n"))            # Warnings are collected in a separate list
  else:
    _ERROR_LOG.extend(err_line.split("\n"))                         # Append traditional error line to the CI error log

  if WARNING:                                                       # CI flag: raise warning during pytest
    warnings.warn_explicit(text,category,filename=module,lineno=len(_ERROR_LOG))
    return
  else:
    if category is not Warning:
      print_error_header()
    if strings.rich_err_color and err_name in err_class_map:
      err_code = err_class_map[err_name]
      strings.print_colored_text(
        strings.pad_err_code(err_code),
        err_color_map.get(err_code,'yellow'),
        stderr=True)
      mod_txt = f'{module}: ' if module else ''                     # Skip module header if it's explicitly set to empty
      print(f'{mod_txt}{text}',file=sys.stderr)
    else:
      print(err_line,file=sys.stderr)

  if more_hints is not None:                                        # Caller supplied hints, print them with HINT label
    print_more_hints(more_hints)

  if more_data is not None:                                         # Caller supplied data, print it with DATA label
    print_more_hints(more_data,'DATA','bright_black')

  if hint is None:                                                  # No pointers to static hints
    return

  from ..data.global_vars import get_topology
  from .strings import extra_data_printout

  topology = get_topology()
  if topology is None:                                              # No valid topology ==> no static hints
    return

  mod_hints = topology.defaults.hints[module]                       # Get static hints for current module

  if mod_hints[hint]:                                               # Do we know what to do?
    hint_printout = extra_data_printout(mod_hints[hint],width=90)   # Format the hint for traditional printout
    _ERROR_LOG.extend(hint_printout.split("\n"))
    if strings.rich_err_color:
      l_width = min(strings.rich_err_width-10,100)
      hint_lines = strings.wrap_text_into_lines(mod_hints[hint],width=l_width)
      print_more_hints(hint_lines,'HINT','green')
    else:
      print(hint_printout,file=sys.stderr)

    mod_hints[hint] = ''

def exit_on_error() -> None:
  global _ERROR_LOG
  if _ERROR_LOG:
    fatal('Cannot proceed beyond this point due to errors, exiting')

def pending_errors() -> bool:
  global _ERROR_LOG
  return True if _ERROR_LOG else False

def repeat_warnings(cmd: str) -> None:
  global _WARNING_LOG
  if _WARNING_LOG:
    wlist = list(_WARNING_LOG)
    print("",file=sys.stderr)
    error(
      text=f"The following warnings were generated during the '{cmd}' processing",
      category=Warning,
      module='',
    )
    for wline in wlist:
      error(wline,category=Warning,module='')

"""
Print colored status headers
"""
def status_created() -> None:
  strings.print_colored_text('[CREATED] ','green','Created ')

def status_success() -> None:
  strings.print_colored_text('[SUCCESS] ','green','OK: ')

def section_header(label: str, text: str, color: str = 'green') -> None:
  if not strings.rich_color:
    print(f'{label} {text}')
  else:
    print()
    table = rich.table.Table(show_header=False)
    l_width = min(strings.rich_width-2,80)
    table.add_column(width=l_width)
    table.add_row(f'[{color}]{label.upper()}[/{color}] {text}')
    strings.rich_console.print(table)

#
# Logging and debugging functions
#

def set_verbose(value: typing.Optional[int] = 1) -> None:
  global VERBOSE
  VERBOSE = 0 if value is None else value

def print_verbose(t: typing.Any) -> None:
  if VERBOSE:
    print(t)

#
# Sets common flags based on parsed arguments.
#
# Internal debugging flags (RAISE_ON_ERROR, WARNING) cannot be set with this function
#
def set_logging_flags(args: typing.Union[argparse.Namespace,Box]) -> None:
  global VERBOSE, LOGGING, DEBUG, QUIET, WARNING, RAISE_ON_ERROR
  global _error_header_printed
  
  if 'verbose' in args and args.verbose:
    VERBOSE = args.verbose

  if 'logging' in args and args.logging:
    LOGGING = True

  if 'test' in args and args.test and 'errors' in args.test:
    QUIET = True

  if 'debug' in args:
    if args.debug is None:
      DEBUG = None
    else:
      DEBUG = args.debug if args.debug else ['all']
      print(f'Debugging flags set: {DEBUG}')

  if 'test' in args and args.test and 'errors' in args.test:
    _error_header_printed = True

  if 'quiet' in args and args.quiet:
    QUIET = True

  if 'warning' in args and args.warning:
    WARNING = True

  if 'raise_on_error' in args and args.raise_on_error:
    RAISE_ON_ERROR = True

#
# Sets zero or more common flags and returns current settings.
#
# There must be a better way of doing it, but this is simple and it works
#
def set_flag(
      debug: typing.Optional[typing.List[str]] = None,
      quiet: typing.Optional[bool] = None,
      verbose: typing.Optional[int] = None,
      logging: typing.Optional[bool] = None,
      warning: typing.Optional[bool] = None,
      raise_error: typing.Optional[bool] = None) -> dict:
  global DEBUG, VERBOSE, LOGGING, QUIET, RAISE_ON_ERROR, WARNING

  DEBUG = debug if debug is not None else DEBUG
  QUIET = quiet if quiet is not None else QUIET
  VERBOSE = verbose if verbose is not None else VERBOSE
  LOGGING = logging if logging is not None else LOGGING
  WARNING = warning if warning is not None else WARNING
  RAISE_ON_ERROR = raise_error if raise_error is not None else RAISE_ON_ERROR

  return {
    'debug': DEBUG,
    'quiet': QUIET,
    'verbose': VERBOSE,
    'logging': LOGGING,
    'raise_on_error': RAISE_ON_ERROR,
    'warning': WARNING
  }

def debug_active(flag: str) -> bool:
  if not DEBUG:
    return False

  return 'all' in DEBUG or flag in DEBUG

"""
init_log_system: initialize the logging system (used to run test cases)
"""
def init_log_system(header: bool = True) -> None:
  global _ERROR_LOG,_error_header_printed

  _ERROR_LOG = []                                 # Clear the error log
  _error_header_printed = not header              # Mark header as printed if we don't want to have one

  _types.init_wrong_type()

def get_error_log() -> list:
  global _ERROR_LOG

  return _ERROR_LOG
