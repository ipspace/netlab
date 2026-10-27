#
# Configuration collection utility functions
#

import argparse
import os
import subprocess
import typing

from box import Box

from ...augment import devices as a_devices
from ...utils import log
from .. import error_and_exit, fs_cleanup


def collectable(nodeset: list, topology: Box) -> typing.Tuple[list,list]:
  """
  Return a list of devices from which the configuration can be collected. Generate
  warning for unsupported devices and exit if no feasible nodes are found.
  """
  n_miss: list = []
  n_list: list = []
  d_miss: set = set()
  defaults = topology.defaults

  for n in nodeset:
    ndata = topology.nodes[n]
    features = a_devices.get_device_features(ndata,defaults)
    if not features.get('initial.collect',False):
      d_miss.add(ndata.device)
      n_miss.append(n)
    else:
      n_list.append(n)

  if n_miss:
    log.warning(
      text='Cannot collect information from device(s) '+','.join(sorted(d_miss)),
      module='collect',
      more_data='Node(s): '+','.join(n_miss))

  if not n_list:
    error_and_exit('Cannot collect information from any of the specified node(s), exiting')

  return (n_list,n_miss)

def create_output(path: str) -> None:
  """
  Cleans up and recreates the configuration collection directory
  """

  fs_cleanup([ path ])
  try:
    os.mkdir(path)
  except Exception as ex:
    log.fatal(f"Cannot create output directory {path}: {ex}")

  if not log.QUIET:
    log.info(f"Collecting configs into {path}")

def get_tarball_file(tarball: str) -> str:
  """
  Get the tarball name
  """
  if not '.tar' in tarball:
    tarball = tarball + '.tar.gz'
  return tarball

def create_tar(args: argparse.Namespace, run_dir: str) -> None:
  tarball = get_tarball_file(args.tar)
  if not args.quiet:
    log.section_header('Create',f'Creating tar archive {tarball}')

  if os.getcwd() != run_dir:
    if not args.quiet:
      log.status_green('CHANGED','')
      print(f'Changing current directory back to {run_dir}')
    os.chdir(run_dir)

  tar_flags = 'cf'
  if '.gz' in tarball:
    tar_flags += 'z'

  if log.VERBOSE:
    tar_flags += 'v'
  try:
    subprocess.check_call(['tar',tar_flags,tarball,args.output])
    if log.VERBOSE:
      print()
    log.info(f'Tarball {tarball} created from {args.output} config directory')
  except Exception as ex:
    log.fatal(f"Cannot start tar: {ex}")

  if args.cleanup:
    if not args.quiet:
      log.section_header('Cleanup','Removing temporary configuration directory')
    fs_cleanup([ args.output ],args.verbose)
    log.info(f'Config directory {args.output} removed')
