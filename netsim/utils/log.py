#
# Common routines for create-topology script
#
import argparse
import inspect
import os
import sys
import typing
import warnings

import rich.table
from box import Box

from ..data import types as _types
from . import strings

LOGGING : bool = False
VERBOSE : int = 0
DEBUG : typing.Optional[typing.List[str]] = None
QUIET : bool = False

RAISE_ON_ERROR : bool = False
WARNING : bool = False

AF_LIST = ('ipv4','ipv6')
BGP_AF  = ('ipv4','ipv6','vpnv4','vpnv6','6pe','evpn')
BGP_SESSIONS = ('ibgp','ebgp')

_ERROR_LOG: list = []
_WARNING_LOG: list = []
_HINTS_CACHE: list = []

err_class_map = {                       # Map error classes into short error codes
  'MissingDependency':  'DEPEND',
  'MissingValue':       'MISSING',
  'IncorrectValue':     'VALUE',
  'IncorrectAttr':      'ATTR',
  'IncorrectType':      'TYPE',
  'FatalError':         'FATAL',
  'UserWarning':        'WRONG',
  'ErrorAbort':         'ERROR',
  'Warning':            'WARNING'
}

err_color_map = {
  'FATAL':   'red',
  'ERROR':   'red',
  'WARNING': 'yellow',
  'INFO':    'bright_cyan'
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

class Result(Exception):            # Used to pass validation result far up the chain
  pass

class Skipped(Exception):           # Used to pass "can't do that" validation message up the chain
  pass

# Try to print 'Errors encountered while processing _filename_' header
#

_error_header_printed: bool = False

"""
Print "errors found in _topologyname_" error header
"""
def print_error_header(indent: int = 10) -> None:
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
        strings.print_colored_text(strings.pad_err_code('ERRORS',indent),'red',stderr=True)
        print(f'Errors found in {toponame}',file=sys.stderr)
      else:                                     # Plain old teletype (or file), print error message
        print(f'Errors encountered while processing {toponame}',file=sys.stderr)
      _error_header_printed = True
  except:
    pass

"""
Print the final error message and abort
"""
def fatal(text: str, module: str = 'netlab', header: bool = False, indent: int = 10) -> typing.NoReturn:
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
        print_error_header(indent)
      if strings.rich_err_color:                  # Color-capable terminal
        strings.print_colored_text(strings.pad_err_code('FATAL',indent),'red',stderr=True)
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
      h_warning: bool=False,            # is this a warning hint?
      cleanup: bool=True,               # Remove empty lines from hint lines?
      indent: int = 10) -> None:

  if isinstance(h_list,str):
    h_width = min(strings.rich_err_width,100)
    if strings.rich_err_color:
      h_width = h_width - indent

    h_list = strings.wrap_text_into_lines(h_list,width=h_width)

  if cleanup:
    h_list = [ line for line in h_list if line ]
  if not h_list:
    return

  global _ERROR_LOG
  h_first = True
  for line in h_list:
    if not h_warning:
      _ERROR_LOG.append(f"... {line}")                      # Convention: hints in traditional output are prefaced with ...
    if strings.rich_err_color:
      if h_first:                                           # First hint line on color-capable TTY: print hint header
        strings.print_colored_text(strings.pad_err_code(h_name,indent),h_color,stderr=True)
        print(strings.wrap_error_message(line,indent),file=sys.stderr)
        h_first = False
      else:
        print(
          " "*indent+strings.wrap_error_message(line,indent),
          file=sys.stderr)                                  # Otherwise print another line indented to align with the previous one
    else:
      print(f"... {line}",file=sys.stderr)                  # Teletype/file, just print the line

"""
If needed, get the module name that called an error function. Return whatever the caller
supplied if it's not none, otherwise inspect the stack.
"""
def get_calling_module(module: typing.Optional[str]) -> str:
  if module is not None:
    return module or 'topology'

  try:
    err_caller = inspect.stack()[2].filename
    return os.path.splitext(os.path.basename(err_caller))[0]
  except:
    return 'unknown'

"""
Display an error message, including error category, calling module and optional hints

When called with calling module set to None, the function uses stack trace to find out
which module called it. The display of the calling module is skipped if the module is
set to '-' and the category is Warning (used to repeat warnings)
"""
def error(
      text: str,                                                    # Error text
      category: typing.Union[typing.Type[Warning],typing.Type[Exception]] = UserWarning,
      module: typing.Optional[str] = None,                          # Module generating the error
      hint: typing.Optional[str] = None,                            # Pointer to a static hint
      more_hints: typing.Optional[typing.Union[str,list]] = None,   # More hints or extra data
      more_data: typing.Optional[typing.Union[str,list]] = None,
      indent: int = 10,
      skip_header: typing.Optional[bool] = None,
      exit_on_error: bool = False) -> None:

  global _ERROR_LOG,err_class_map,_WARNING_LOG,_HINTS_CACHE,QUIET,err_color_map,_error_header_printed

  module = '' if module == '-' else get_calling_module(module)
  err_name = category.__name__
  err_line = f'{err_name} in {module}: {text}' if module else f'{err_name}: {text}'

  if skip_header is not None:
    _error_header_printed = skip_header

  if category is Warning:
    if QUIET:
      return
    _WARNING_LOG.extend(f'{module}: {text}'.split("\n"))            # Warnings are collected in a separate list
  else:
    _ERROR_LOG.extend(err_line.split("\n"))                         # Append traditional error line to the CI error log

  if WARNING and isinstance(category,Warning):                      # CI flag: raise warning during pytest
    warnings.warn_explicit(text,category,filename=module,lineno=len(_ERROR_LOG))
    return
  else:
    if category is not Warning:
      print_error_header(indent)
    if strings.rich_err_color and err_name in err_class_map:
      err_code = err_class_map[err_name]
      strings.print_colored_text(
        strings.pad_err_code(err_code,indent),
        err_color_map.get(err_code,'yellow'),
        stderr=True)
      mod_txt = f'{module}: ' if module else ''                     # Skip module header if it's explicitly set to empty
      print(strings.wrap_error_message(f'{mod_txt}{text}',indent),file=sys.stderr)
    else:
      print(err_line,file=sys.stderr)

  if more_data is not None:                                         # Caller supplied data, print it with DATA label
    print_more_hints(more_data,'DATA','bright_black',h_warning=category is Warning,indent=indent)

  if more_hints is not None:                                        # Caller supplied hints, print them with HINT label
    if more_hints not in _HINTS_CACHE:
      print_more_hints(more_hints,h_warning=category is Warning,indent=indent)
    _HINTS_CACHE.append(more_hints)

  if hint is None:                                                  # No pointers to static hints
    if exit_on_error and category is not Warning:
      sys.exit(1)
    return

  from ..data.global_vars import get_topology
  from .strings import extra_data_printout

  topology = get_topology()
  if topology is None:                                              # No valid topology ==> no static hints
    if exit_on_error and category is not Warning:
      sys.exit(1)
    return

  mod_hints = topology.defaults.hints[module]                       # Get static hints for current module
  if mod_hints[hint]:                                               # Do we know what to do?
    hint_printout = extra_data_printout(mod_hints[hint],width=90)   # Format the hint for traditional printout
    if category is not Warning:
      _ERROR_LOG.extend(hint_printout.split("\n"))
    if strings.rich_err_color:
      l_width = min(strings.rich_err_width-indent,100)
      hint_lines = strings.wrap_text_into_lines(mod_hints[hint],width=l_width)
      print_more_hints(hint_lines,'HINT','green',h_warning=category is Warning)
    else:
      print(hint_printout,file=sys.stderr)

    mod_hints[hint] = ''

  if exit_on_error and category is not Warning:
    sys.exit(1)

"""
Print a warning. The arguments are similar to the 'error' function apart from:

* Category is assumed to be 'Warning'
* The 'flag' argument specifies a defaults setting to check. If it includes a dot, it's
  assumed to be a global warning (under defaults.warnings), otherwise it's a module-level
  warning (under defaults._module_.warnings).
"""
def warning(*,
      text: str,
      module: typing.Optional[str] = None,
      flag: typing.Optional[str] = None,
      **kwargs: typing.Any) -> None:

  global _HINTS_CACHE

  module = get_calling_module(module)
  if flag is None:
    error(text,category=Warning,module=module,**kwargs)
    return

  if flag.startswith('defaults.'):
    pass
  elif '.' in flag:
    flag = f'defaults.warnings.{flag}'
  else:
    flag = f'defaults.{module}.warnings.{flag}'

  from ..data import global_vars
  topology = global_vars.get_topology()
  flag_value = topology[flag] if topology is not None else True
  if flag_value is False:
    return

  if flag_value == 'error':
    kwargs['category'] = ErrorAbort
  if 'category' not in kwargs:
    kwargs['category'] = Warning

  # Add the 'this is how you disable this warning' hint
  #
  q_disable = 'hide this warning' if kwargs['category'] is Warning else 'disable this check'
  q_hint = f'Set {flag} to False to {q_disable}'                          # The 'disable me' hint
  c_hint = kwargs.get('more_hints',None)                                  # The caller hint
  if c_hint in _HINTS_CACHE:                                              # Was the caller hint already displayed?
    c_hint = None

  if q_hint not in _HINTS_CACHE:                                          # Did we already tell the user how to do it?
    if c_hint is None:                                                    # Did the caller supply a unique hint?
      kwargs['more_hints'] = [ q_hint ]
    elif isinstance(c_hint,list):                                         # Append to existing hint list?
      kwargs['more_hints'] = c_hint + [ q_hint ]
    elif isinstance(c_hint,str):                                          # Add second line to the existing hint?
      kwargs['more_hints'] = [ c_hint, q_hint ]
    else:                                                                 # Otherwise we can't hint
      q_hint = ''

    if q_hint:                                                            # If we managed to squeeze in our hint...
      _HINTS_CACHE.append(q_hint)                                         # ... make sure we don't do it twice

  error(text,module=module,**kwargs)                                      # And finally, generate the warning
  if c_hint:                                                              # ... and add the caller hint (if any)
    _HINTS_CACHE.append(c_hint)                                           # ... to the displayed hints

"""
Print informational message. The arguments are similar to the ones used in 'error' function
"""
def info(
      text: str,                                                    # Information text
      module: str = '',                                             # Module generating the information text
      more_hints: typing.Optional[typing.Union[str,list]] = None,   # More hints or extra data
      more_data: typing.Optional[typing.Union[str,list]] = None,
      indent: int = 10) -> None:

  global err_color_map

  mod_txt = f'{module}: ' if module else ''                     # Skip module header if it's explicitly set to empty
  if strings.rich_err_color:
    r_color = err_color_map['INFO']
    strings.print_colored_text(strings.pad_err_code('INFO',indent),r_color)
  else:
    mod_txt += ' [INFO] '

  print(strings.wrap_error_message(f'{mod_txt}{text}',indent))
  if more_hints is not None:                                        # Caller supplied hints, print them with HINT label
    print_more_hints(more_hints,h_warning=True,indent=indent)

  if more_data is not None:                                         # Caller supplied data, print it with DATA label
    print_more_hints(more_data,'DATA','bright_black',h_warning=True,indent=indent)

def get_error_count() -> int:
  global _ERROR_LOG
  return len(_ERROR_LOG)

def exit_on_error(max_err: int = 0) -> None:
  global _ERROR_LOG
  if len(_ERROR_LOG) > max_err:
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
      module='-',
    )
    for wline in wlist:
      error(wline,category=Warning,module='-')

"""
Print colored status headers
"""
def status_green(stat: str, txt: str) -> None:
  stat = f'[{stat}]'
  strings.print_colored_text(f'{stat:10s}','green',txt)

def status_created() -> None:
  status_green('CREATED','Created')

def status_success() -> None:
  status_green('SUCCESS','OK: ')

"""
Partial success status
"""
def partial_success(s_cnt: int, t_cnt: int) -> None:
  if s_cnt == t_cnt:
    status_success()
  elif s_cnt == 0:
    strings.print_colored_text(strings.pad_err_code('ERROR'),'red')
  else:
    strings.print_colored_text(strings.pad_err_code('PARTIAL'),'yellow')

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
  global _ERROR_LOG,_HINTS_CACHE,_error_header_printed

  _ERROR_LOG = []                                 # Clear the error log
  _HINTS_CACHE = []                               # And the hints cache
  _error_header_printed = not header              # Mark header as printed if we don't want to have one

  _types.init_wrong_type()

def get_error_log() -> list:
  global _ERROR_LOG

  return _ERROR_LOG
