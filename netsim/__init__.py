#!/usr/bin/env python3

import sys

__version__ = "1.8.0-post1"

try:
  import box

  if box.__version__ < '7.0':                 # netlab needs Python Box version 7.0 or higher
    print("FATAL ERROR: python-box version 7.0 or higher required, use 'pip3 install --upgrade python-box' to install")
    sys.exit(1)
except:                                       # box is not installed, something else is bound to fail ;)
  pass
