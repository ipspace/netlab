#!/usr/bin/env python3
#
# Print netlab usage
#

import sys
import typing

try:
  from importlib import resources
except ImportError:
  import importlib_resources as resources # type: ignore

def print_usage(fname: str) -> None:
  package = '.'.join(__name__.split('.')[:-1])
  with resources.open_text(package,fname) as fid:
    print(fid.read())

def run(args: typing.List[str]) -> None:
  print_usage('usage.txt')
