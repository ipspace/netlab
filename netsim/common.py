#
# Common routines for create-topology script
#
import sys
import typing
import warnings
from jinja2 import Environment, PackageLoader, StrictUndefined, make_logging_undefined

LOGGING=False
VERBOSE=False
RAISE_ON_ERROR=False
err_count = 0

class MissingValue(Warning):
  pass

class IncorrectValue(Warning):
  pass

class FatalError(Warning):
  pass

class ErrorAbort(Exception):
  pass

def fatal(text: str, module: str = 'topology') -> None:
  global err_count
  err_count = err_count + 1
  warnings.warn_explicit(text,FatalError,filename=module,lineno=err_count)
  if RAISE_ON_ERROR:
    raise ErrorAbort(text)
  else:
    sys.exit(1)

def error(text: str, category: typing.Type[Warning] = UserWarning, module: str = 'topology') -> None:
  global err_count
  err_count = err_count + 1
  warnings.warn_explicit(text,category,filename=module,lineno=err_count)
#  print(text,file=sys.stderr)

def exit_on_error() -> None:
  global err_count
  if err_count > 0:
    fatal('Cannot proceed beyond this point due to errors, exiting')

def template(j2: str , data: typing.Dict, path: str) -> str:
  ENV = Environment(loader=PackageLoader('netsim',path), \
          trim_blocks=True,lstrip_blocks=True, \
          undefined=make_logging_undefined(base=StrictUndefined))
  template = ENV.get_template(j2)
  return template.render(**data)

def null_to_string(d: typing.Dict) -> None:
  for k in d.keys():
    if isinstance(d[k],dict):
      null_to_string(d[k])
    elif d[k] is None:
      d[k] = ""

def set_verbose() -> None:
  global VERBOSE
  VERBOSE=True

def print_verbose(t: typing.Any) -> None:
  if VERBOSE:
    print(t)
