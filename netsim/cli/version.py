#!/usr/bin/env python3
#
# Print netlab usage
#

import importlib
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
  'ansible': 'ansible-core'
}

MISSING_OK = ['ruamel.yaml']

def print_default_locations() -> None:
  try:
    topology = _read.load('package:cli/empty.yml')
    print(f"  user defaults: {[ src for src in topology.input if 'package:' not in src ]}")
  except Exception as ex:
    print(f"  cannot load default topology: {str(ex)}")

def run(args: typing.List[str]) -> None:
  global MODULES, MISSING_OK

  print(f"netlab version {netsim.__version__}")
  print(f"  executable location: {NETLAB_SCRIPT}")
  print(f"  package location: {netsim.__path__}")
  print_default_locations()
  print("\nRequired packages:")
  for module,package in MODULES.items():
    try:
      py_mod = importlib.import_module(module)
      try:
        version = getattr(py_mod,'__version__')
        print(f'  {package}: {version}')
      except Exception as ex:
        print(f'  Cannot find {package} version: {str(ex)}')
    except Exception as ex:
      if package not in MISSING_OK:
        print(f'  {package}: not installed {str(ex)}')
