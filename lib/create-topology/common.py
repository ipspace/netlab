#
# Common routines for create-topology script
#
import sys
import os
from jinja2 import Environment, FileSystemLoader, Undefined, StrictUndefined, make_logging_undefined

LOGGING=False
VERBOSE=False

def fatal(text):
  print('FATAL: %s' % text,file=sys.stderr)
  sys.exit(1)

err_count = 0

def error(text):
  global err_count
  print(text,file=sys.stderr)
  err_count = err_count + 1

def exit_on_error():
  global err_count
  if err_count > 0:
    sys.exit(1)

def template(j2,data,path):
  ENV = Environment(loader=FileSystemLoader(path), \
          trim_blocks=True,lstrip_blocks=True, \
          undefined=make_logging_undefined(base=StrictUndefined))
  template = ENV.get_template(j2)
  return template.render(**data)

def get_value(data,path=[],default=None):
  for k in path:
    if not(type(data) is dict):
      return data
    if not k in data:
      return default
    data = data.get(k)
  return data

def get_default(data,key,path=[],default=None):
  if key in data:
    return data[key]
  return get_value(data=data,path=path,default=default)

def merge_defaults(data,defaults):
  if not data:
    return defaults

  if type(data) is dict and type(defaults) is dict:
    for (k,v) in defaults.items():
      if not k in data or isinstance(data.get(k),dict):
        data[k] = merge_defaults(data.get(k),defaults[k])
  return data

def set_verbose():
  VERBOSE=True

def print_verbose(t):
  if VERBOSE:
    print(t)
