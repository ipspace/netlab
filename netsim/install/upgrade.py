import json
import os
import site
import sys
from importlib import metadata
from pathlib import Path

from box import Box

from netsim.cli import error_and_exit
from netsim.utils import log


def pre_check(topology: Box) -> bool:
  """
  Upgrade the networklab package in the same Python environment and location
  it was installed into, and refuse to touch development (editable) installs
  """
  try:
    dist = metadata.distribution('networklab')
  except metadata.PackageNotFoundError:
    error_and_exit(
      'netlab is not installed as a Python package, cannot upgrade it',
      more_hints='Are you running netlab from a git repository? Use "git pull" to upgrade it')

  direct_url = json.loads(dist.read_text('direct_url.json') or '{}')
  if direct_url.get('dir_info',{}).get('editable',False):
    error_and_exit(
      'netlab is installed in development (editable) mode, refusing to replace it with a PyPI release',
      more_hints=f'Use "git pull" in {direct_url.get("url","").removeprefix("file://")} to upgrade it')

  os.environ['PYTHON'] = sys.executable           # Use the Python interpreter running netlab
  args = topology.defaults.netlab.args
  if sys.prefix != sys.base_prefix:               # Running in a (not necessarily activated) venv
    os.environ['VIRTUAL_ENV'] = sys.prefix        # ... make check_script treat it as such
  elif Path(str(dist.locate_file(''))).resolve() == Path(site.getusersitepackages()).resolve():
    args.user = True                              # Installed in user .local directory
  else:
    args.system = True                            # Installed in system directories

  log.info(f'Upgrading networklab {dist.version} installed in {dist.locate_file("")}')
  return True
