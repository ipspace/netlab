#!/usr/bin/env python3
#
# Print netlab usage
#

import sys
import typing
import netsim

def run(args: typing.List[str]) -> None:
  print("netlab version %s" % netsim.__version__)
