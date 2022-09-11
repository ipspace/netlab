#
# Common routines for create-topology script
#
import sys
import typing
import warnings
import argparse
import os
import textwrap
import pathlib

from jinja2 import Environment, PackageLoader, FileSystemLoader, StrictUndefined, make_logging_undefined
from box import Box,BoxList

LOGGING : bool = False
VERBOSE : int = 0
DEBUG : typing.Optional[typing.List[str]] = None
QUIET : bool = False

RAISE_ON_ERROR : bool = False
WARNING : bool = False

AF_LIST = ['ipv4','ipv6']
BGP_SESSIONS = ['ibgp','ebgp']

err_count : int = 0
netsim_package_path = os.path.abspath(os.path.dirname(__file__))

class MissingValue(Warning):
  pass

class IncorrectValue(Warning):
  pass

class IncorrectType(Warning):
  pass

class FatalError(Warning):
  pass

class ErrorAbort(Exception):
  pass

def fatal(text: str, module: str = 'netlab') -> None:
  global err_count
  err_count = err_count + 1
  if RAISE_ON_ERROR:
    raise ErrorAbort(text)
  else:
    if WARNING:
      warnings.warn_explicit(text,FatalError,filename=module,lineno=err_count)
    else:
      print(f'Fatal error in {module}: {text}',file=sys.stderr)
    sys.exit(1)

def error(text: str, category: typing.Type[Warning] = UserWarning, module: str = 'topology') -> None:
  global err_count
  err_count = err_count + 1
  if WARNING:
    warnings.warn_explicit(text,category,filename=module,lineno=err_count)
  else:
    print(f'{category.__name__} in {module}: {text}',file=sys.stderr)

def exit_on_error() -> None:
  global err_count
  if err_count > 0:
    fatal('Cannot proceed beyond this point due to errors, exiting')

def extra_data_printout(s : str) -> str:
  return textwrap.TextWrapper(
    initial_indent="... ",
    subsequent_indent="      ").fill(s)

#
# File functions
#

def open_output_file(fname: str) -> typing.TextIO:
  if fname == '-':
    return sys.stdout

  return open(fname,mode='w')

def close_output_file(f: typing.TextIO) -> None:
  if f.name != '<stdout>':
    f.close()

def print_yaml(x : typing.Any) -> str:
  if isinstance(x,dict):
    return Box(x).to_yaml()
  elif isinstance(x,list):
    return BoxList(x).to_yaml()
  else:
    return str(x)

def get_moddir() -> pathlib.Path:
  return pathlib.Path(__file__).resolve().parent

def template(j2: str , data: typing.Dict, path: str, user_template_path: typing.Optional[str] = None) -> str:
  template_path = [ str(get_moddir()) + "/" + path ]
  if not user_template_path is None:
    template_path = [ './' + user_template_path, os.path.expanduser('~/.netlab/'+user_template_path) ] + template_path
  if debug_active('template'):
    print(f"TEMPLATE PATH for {j2}: {template_path}")
  ENV = Environment(loader=FileSystemLoader(template_path), \
          trim_blocks=True,lstrip_blocks=True, \
          undefined=make_logging_undefined(base=StrictUndefined))
  template = ENV.get_template(j2)
  return template.render(**data)

#
# write_template: Applies a custom template (in_folder/j2) and writes it to the given file path (out_folder/filename)
#
def write_template(in_folder: str, j2: str, data: typing.Dict, out_folder: str, filename: str) -> None:
  if debug_active('template'):
    print(f"write_template {in_folder}/{j2} -> {out_folder}/{filename}")
  pathlib.Path(out_folder).mkdir(parents=True, exist_ok=True)
  out_file = f"{out_folder}/{filename}"
  with open(out_file,mode='w') as output:
    output.write(template(j2,data,in_folder))

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
  RAISE_ON_ERROR = raise_error  if raise_error is not None else RAISE_ON_ERROR

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
