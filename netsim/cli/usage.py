#!/usr/bin/env python3
#
# Print netlab usage
#

import sys
import typing

from importlib import resources

def print_usage(fname: str) -> None:
  package = '.'.join(__name__.split('.')[:-1])
  with resources.open_text(package,fname) as fid:
    print(fid.read())

def run(args: typing.List[str]) -> None:
  print_usage('usage.txt')
