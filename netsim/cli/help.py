#!/usr/bin/env python3
#
# Print netlab usage
#

import typing
from importlib import resources

from netsim.utils import strings


def print_usage(fname: str) -> None:
  package = '.'.join(__name__.split('.')[:-1])
  strings.rich_console.print(resources.files(package).joinpath(fname).read_text())

def run(args: typing.List[str]) -> None:
  print_usage('usage.txt')
