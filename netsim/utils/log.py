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
from .strings import rich_err_color,print_colored_text,pad_err_code,pad_text

LOGGING : bool = False
VERBOSE : int = 0
DEBUG : typing.Optional[typing.List[str]] = None
QUIET : bool = False

RAISE_ON_ERROR : bool = False
WARNING : bool = False

AF_LIST = ['ipv4','ipv6']
BGP_SESSIONS = ['ibgp','ebgp']

_ERROR_LOG: list = []

err_class_map = {
  'MissingDependency':  'DEPEND',
  'MissingValue':       'MISSING',
  'IncorrectValue':     'VALUE',
  'IncorrectAttr':      'ATTR',
  'IncorrectType':      'TYPE',
  'FatalError':         'FATAL',
  'UserWarning':        'WRONG'
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

def print_error_header() -> None:
  global _error_header_printed
  if _error_header_printed:
    return
  
  try:
    from ..data import global_vars
    topology = global_vars.get_topology()
    if not topology:
      return

    if topology.input:
      toponame = os.path.basename(topology.input[0])
      if rich_err_color:
        print_colored_text(pad_err_code('ERRORS'),'red',stderr=True)
        print(f'Errors found in {toponame}',file=sys.stderr)
      else:
        print(f'Errors encountered while processing {toponame}',file=sys.stderr)
      _error_header_printed = True
  except:
    pass

def fatal(text: str, module: str = 'netlab') -> typing.NoReturn:
  global _ERROR_LOG

  err_line = f'Fatal error in {module}: {text}'
  _ERROR_LOG.extend(err_line.split("\n"))

  if RAISE_ON_ERROR:
    raise ErrorAbort(text)
  else:
    if WARNING:
      warnings.warn_explicit(text,FatalError,filename=module,lineno=len(_ERROR_LOG))
    else:
      print_error_header()
      if rich_err_color:
        print_colored_text(pad_err_code('FATAL'),'red',stderr=True)
        if module != 'netlab':
          print(f'{module}: ',end='',file=sys.stderr)
        print(text,file=sys.stderr)
      else:
        print(err_line,file=sys.stderr)
    sys.exit(1)

"""
Display an error message, including error category, calling module and optional hint
"""

def print_more_hints(h_list: list,h_name: str='HINT',h_color: str='green') -> None:
  if not h_list:
    return

  global _ERROR_LOG
  h_first = True
  for line in h_list:
    _ERROR_LOG.append(f"... {line}")
    if rich_err_color:
      if h_first:
        print_colored_text(pad_err_code(h_name),h_color,stderr=True)
        print(line,file=sys.stderr)
        h_first = False
      else:
        print(" "*10+line,file=sys.stderr)
    else:
      print(f"... {line}",file=sys.stderr)

def error(
      text: str,
      category: typing.Type[Warning] = UserWarning,
      module: str = 'topology',
      hint: typing.Optional[str] = None,
      more_hints: typing.Optional[list] = None,
      more_data: typing.Optional[list] = None) -> None:

  global _ERROR_LOG,err_class_map
  err_name = category.__name__
  err_line = f'{err_name} in {module}: {text}'
  _ERROR_LOG.extend(err_line.split("\n"))

  if WARNING:
    warnings.warn_explicit(text,category,filename=module,lineno=len(_ERROR_LOG))
    return
  else:
    print_error_header()
    if rich_err_color and err_name in err_class_map:
      print_colored_text(pad_err_code(err_class_map[err_name]),'yellow',stderr=True)
      print(f'{module}: {text}',file=sys.stderr)
    else:
      print(err_line,file=sys.stderr)

  if more_hints is not None:
    more_hints = [ line for line in more_hints if line ]
    print_more_hints(more_hints)

  if more_data is not None:
    more_data =  [ line for line in more_data if line ]
    print_more_hints(more_data,'DATA','bright_black')
  if hint is None:                                  # No extra hints
    return

  from ..data.global_vars import get_topology
  from .strings import extra_data_printout

  topology = get_topology()
  if topology is None:                              # No valid topology ==> no hints
    return

  mod_hints = topology.defaults.hints[module]       # Get hints for current module

  if mod_hints[hint]:
    hint_printout = extra_data_printout(mod_hints[hint],width=90)
    _ERROR_LOG.extend(hint_printout.split("\n"))  
    print(hint_printout,file=sys.stderr)
    mod_hints[hint] = ''

def exit_on_error() -> None:
  global _ERROR_LOG
  if _ERROR_LOG:
    fatal('Cannot proceed beyond this point due to errors, exiting')

def pending_errors() -> bool:
  global _ERROR_LOG
  return True if _ERROR_LOG else False

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
