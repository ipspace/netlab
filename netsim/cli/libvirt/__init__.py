# 'netsim libvirt' actions

import typing

from ...utils import log
from ...utils import read as _read
from . import config, package, remove


def libvirt_usage() -> None:
  print("""
Usage:

    netlab libvirt <action> <parameters>

The 'netlab libvirt' command can execute the following actions:

package   Help you create a Vagrant box from a qcow/vmdk virtual disk
config    Print the build recipe for the specified Vagrant box
remove    Remove the specified Vagrant box or related libvirt volumes
        
Use 'netlab libvirt <action> --help' to get action-specific help
""")

def run(cli_args: typing.List[str]) -> None:
  topology = _read.system_defaults(include_user=True)
  if not topology:
    log.fatal("Cannot read the system defaults","libvirt")

  if not cli_args:
    libvirt_usage()
    return

  if cli_args[0] == 'package':
    package.run(cli_args[1:],topology)
  elif cli_args[0] == 'config':
    config.run(cli_args[1:],topology.settings)
  elif cli_args[0] == 'remove':
    remove.run(cli_args[1:],topology)
  else:
    libvirt_usage()
