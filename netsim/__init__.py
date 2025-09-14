#!/usr/bin/env python3

import sys

__version__ = "25.09-post1"

abort = False

try:
  import box
  if box.__version__ < '7.2.0':               # netlab needs Python Box version 7.2.0 or higher
    print("FATAL ERROR: python-box version 7.2.0 or higher required, use 'pip3 install --upgrade python-box' to install")
    abort = True
except:                                       # box is not installed, something else is bound to fail ;)
  pass

try:
  import ansible  # type: ignore
  if ansible.__version__ >= '2.19':           # Ansible core 2.19 contains significant templating changes
    print(f"""
FATAL ERROR: Ansible core version 2.19 or higher breaks netlab templating. See
https://github.com/ipspace/netlab/issues/2683 for details.

Downgrade ansible to version 11.10 or lower, preferably using "netlab install
ansible" command.
""")
    abort = 'install' not in sys.argv         # We should abort unless the user is trying to reinstall ansible
except:
  pass

if abort:
  sys.exit(1)
