#
# Display netlab version and the information about installed libraries
#

import importlib
import importlib.metadata
import typing

import netsim

from ..utils import read as _read
from . import NETLAB_SCRIPT

MODULES: dict = {
  'box': 'python-box',
  'jinja2': 'Jinja2',
  'yaml': 'PyYAML',
  'netaddr': 'netaddr',
  'ruamel.yaml': 'ruamel.yaml',
  'requests': 'requests',
  'filelock': 'filelock'
}

PACKAGES: list = [ 'rich' ]

ANSIBLE_PACKAGES: list = [ 'ansible', 'ansible-core', 'ansible-pylibssh' ]

MISSING_OK = ['ruamel.yaml']

def print_default_locations() -> None:
  try:
    topology = _read.load('package:cli/empty.yml')
    print(f"  user defaults: {[ src for src in topology.input if 'package:' not in src ]}")
  except Exception as ex:
    print(f"  cannot load default topology: {str(ex)}")

def package_version(package: str) -> None:
  try:
    print(f'  {package}: {importlib.metadata.version(package)}')
  except importlib.metadata.PackageNotFoundError:
    print(f'  {package}: not installed')
  except Exception as ex:
    print(f'  Cannot figure out {package} version: {str(ex)}')

def module_version(module: str, package: str, missing_ok: bool = False) -> None:
  try:
    py_mod = importlib.import_module(module)
    try:
      version = getattr(py_mod,'__version__')
      print(f'  {package}: {version}')
    except Exception as ex:
      print(f'  Cannot find {package} version: {str(ex)}')
  except Exception as ex:
    if missing_ok:
      print(f'  {package}: not installed')
    else:
      print(f'  {package}: not installed {str(ex)}')

def run(args: typing.List[str]) -> None:
  global MODULES, PACKAGES, ANSIBLE_PACKAGES, MISSING_OK

  print(f"netlab version {netsim.__version__}")
  print(f"  executable location: {NETLAB_SCRIPT}")
  print(f"  package location: {netsim.__path__}")
  print_default_locations()

  print("\nRequired packages:")
  for module,package in MODULES.items():
    if package not in MISSING_OK:
      module_version(module,package)
  for package in PACKAGES:
    package_version(package)

  print("\nOptional packages:")
  for module,package in MODULES.items():
    if package in MISSING_OK:
      module_version(module,package,missing_ok=True)

  print("\nAnsible components:")
  for package in ANSIBLE_PACKAGES:
    package_version(package)
