#!/usr/bin/env python3

import sys

__version__ = "1.9.3-dev1"

abort = False

if sys.version_info < (3,9):
  print(f"FATAL ERROR: Netlab requires Python version 3.9 or newer - installed {sys.version}")
  abort = True

try:
  import box

  if box.__version__ < '7.2.0':                 # netlab needs Python Box version 7.2 or higher
    print("FATAL ERROR: python-box version 7.2.0 or higher required, use 'pip3 install --upgrade python-box' to install")
    abort = True

except:                                         # box is not installed, something else is bound to fail ;)
  pass

if abort:
  sys.exit(1)
