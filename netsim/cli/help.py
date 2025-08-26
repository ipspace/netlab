#!/usr/bin/env python3
#
# Print netlab usage
#

import typing

from netsim.utils import strings

try:
  from importlib import resources
except ImportError:
  import importlib_resources as resources  # type: ignore

def print_usage(fname: str) -> None:
  package = '.'.join(__name__.split('.')[:-1])
  with resources.open_text(package,fname) as fid:
    strings.rich_console.print(fid.read())

def run(args: typing.List[str]) -> None:
  print_usage('usage.txt')
