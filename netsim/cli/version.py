#!/usr/bin/env python3
#
# Print netlab usage
#

import sys
import typing
from .. import __version__

def run(args: typing.List[str]) -> None:
  print("netsim-tools version %s" % __version__)
