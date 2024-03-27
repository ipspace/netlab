#
# Version checking utilities
#

import typing
import sys
import os
import pathlib
import glob

from packaging import version as _pv,specifiers as _ps

from box import Box
from . import log, files as _files

from .. import __version__

"""
get_version_specifier:
  Given a string (or a number if YAML parser feels like that)
  create a specifier set that matches versions higher or equal to that string
"""
def get_version_specifier(version: typing.Any) -> typing.Optional[_ps.SpecifierSet]:
  try:
    version_string = str(version)
    version_spec = False
    for kw in ('=','>','<'):
      version_spec = version_spec or kw in version_string

    if not version_spec:
      version_string = f'>= {version_string}'
    return _ps.SpecifierSet(version_string)
  except:
    log.error(f'Error parsing version {version}: {str(sys.exc_info()[1])}',log.IncorrectValue,'version')
    return None

"""
get_netlab_version: utility function that transforms __version__ into a packaging Version object
"""
def get_netlab_version() -> _pv.Version:
  netlab_version = _pv.Version(__version__)
  if 'dev' in __version__:          # Workaround: dev versions are not considered to be 'later than' previous releases :(
    netlab_version = _pv.Version(netlab_version.base_version)

  return netlab_version

"""
check_topology_version: verify whether we can process the topology with current netlab version
"""
def check_topology_version(topology: Box) -> None:
  version = topology.get('version',None) or topology.defaults.get('version',None)
  if not version:
    return

  version_set = get_version_specifier(version)
  if version_set is None:
    log.fatal(
      f'Invalid version {version} specified in lab topology or user defaults',
      module='topology',
      header=True)

  if not get_netlab_version() in version_set:
    log.fatal(
      f'Lab topology cannot be processed with netlab version {__version__}, requires {version}',
      module='topology',
      header=True)

"""
get_versioned_topology: given a topology name, find a version of the topology best suited for current netsim version
"""
def get_versioned_topology(toponame: str) -> str:
  topopath = pathlib.Path(toponame)                       # It's easier to work with path objects, convert topology name to path

  file_stem = topopath.stem                               # Get the name stem (we'll need it to extract version)
  file_sfx  = topopath.suffix
  glob_string = file_stem + ".*.*" + file_sfx             # Create glob from topology file name
  netlab_version = get_netlab_version()

  # For /path/x.yml, iterate over /path/x.*.yml
  #
  best_version = None
  for candidate in topopath.parent.glob(glob_string):
    cand_version = candidate.stem[len(file_stem)+1:]      # Extract version from versioned topology name
    cand_spec = get_version_specifier(cand_version)       # Try to get version specifier from the topology version name
    if cand_spec is None:                                 # If the version is weird, we'll get an error message
      log.fatal(
        f'Found invalid Python version {cand_version} in {candidate.name} when looking for the best version of {topopath.name}')

    if not netlab_version in cand_spec:                   # Is netlab version good enough to handle this topology?
      continue                                            # ... nope, keep going

    if best_version is None:                              # Have we found a matching topology version yet?
      best_version = _pv.Version(cand_version)            # ... nope, this is our best chance
    elif best_version in cand_spec:                       # Is the best version we have better than what we found now?
      continue                                            # ... yes, ignore this one
    else:
      best_version = _pv.Version(cand_version)            # Remember the best version we found so far

  if best_version is None:
    return toponame

  selected_name = f"{file_stem}.{best_version}{file_sfx}"
  print(
    f'Notice: using {selected_name} lab topology instead of {topopath.name}',
    file=sys.stderr)

  return str(topopath.parent / selected_name)
