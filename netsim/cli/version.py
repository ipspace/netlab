#!/usr/bin/env python3
#
# Print netlab usage
#

import sys
import typing
import netsim

def run(args: typing.List[str]) -> None:
  print(f"netlab version {netsim.__version__}")
