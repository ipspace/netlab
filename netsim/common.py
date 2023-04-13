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
from .data.global_vars import get_topology

from .utils.log import LOGGING, VERBOSE, DEBUG, QUIET, RAISE_ON_ERROR, WARNING
from .utils.log import MissingValue, IncorrectAttr, IncorrectValue, IncorrectType, FatalError, ErrorAbort
from .utils.log import fatal, error, exit_on_error, set_logging_flags, set_flag, print_verbose, debug_active
from .utils.strings import extra_data_printout,format_structured_dict,print_structured_dict
from .utils.templates import template,write_template,find_file,get_moddir

AF_LIST = ['ipv4','ipv6']
BGP_SESSIONS = ['ibgp','ebgp']

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

ruamel_attrs: typing.Final[dict] = {'version': (1,1)}

def get_yaml_string(x : typing.Any) -> str:
  global ruamel_attrs
  if isinstance(x, Box) or isinstance(x,BoxList):
    return x.to_yaml(ruamel_attrs=ruamel_attrs)
  if isinstance(x,dict):
    return Box(x).to_yaml(ruamel_attrs=ruamel_attrs)
  elif isinstance(x,list):
    return BoxList(x).to_yaml(ruamel_attrs=ruamel_attrs)
  else:
    return str(x)
