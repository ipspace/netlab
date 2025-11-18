#!/usr/bin/env python3

import sys

__version__ = "25.11.01"

abort = False

try:
  import box
  if box.__version__ < '7.2.0':               # netlab needs Python Box version 7.2.0 or higher
    print("FATAL ERROR: python-box version 7.2.0 or higher required, use 'pip3 install --upgrade python-box' to install")
    abort = True
except:                                       # box is not installed, something else is bound to fail ;)
  pass

if abort:
  sys.exit(1)
