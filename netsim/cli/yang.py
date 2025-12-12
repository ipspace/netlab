#
# netlab yang command
#
# Validate topology file using YANG model with MUST statements
#
import argparse
import json
import os
import sys
import typing

from .. import augment
from ..augment.main import transform_setup
from ..utils import log
from ..utils import read as _read
from . import common_parse_args, parser_add_debug, topology_parse_args
from .yang_validator import validate_topology_yang


def yang_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    parents=[ common_parse_args(), topology_parse_args() ],
    prog="netlab yang",
    description='Validate topology file using YANG model with MUST statements')

  parser.add_argument(
    dest='topology',
    action='store',
    nargs='?',
    default='topology.yml',
    help='Topology file to validate (default: topology.yml)')
  
  parser.add_argument(
    '--model',
    dest='yang_model',
    action='store',
    default='package:yang/netlab-topology.yang',
    help='YANG model file to use for validation (default: package:yang/netlab-topology.yang)')
  
  parser.add_argument(
    '--output',
    dest='output',
    action='store',
    choices=['text', 'json'],
    default='text',
    help='Output format (default: text)')
  
  parser.add_argument(
    '--json-cache',
    dest='json_cache',
    action='store',
    help='Use consolidated JSON cache file instead of reading YAML files')
  
  parser_add_debug(parser)
  return parser.parse_args(args)


def run(cli_args: typing.List[str]) -> None:
  args = yang_parse(cli_args)
  log.set_logging_flags(args)
  
  # Set JSON cache if provided
  if hasattr(args, 'json_cache') and args.json_cache:
    _read.set_json_cache(args.json_cache)
  else:
    # Check environment variable as fallback
    json_cache_path = os.environ.get('NETLAB_JSON_CACHE')
    if json_cache_path:
      _read.set_json_cache(json_cache_path)
  
  # Load and transform topology
  # Get topology file - argparse should set this from positional argument
  topology_file = getattr(args, 'topology', 'topology.yml')
  if not topology_file:
    topology_file = 'topology.yml'
  
  topology = _read.load(topology_file, getattr(args, 'defaults', None))
  if topology is None:
    log.fatal(f'Cannot read topology file: {topology_file}')
  
  # Apply CLI settings (device, provider, etc.) before transformation
  # This allows test files without explicit device types to work with -d flag
  if hasattr(args, 'device') and args.device:
    topology.nodes = augment.nodes.create_node_dict(topology.nodes)
    _read.add_cli_args(topology, args)
  
  log.exit_on_error()
  
  # Transform topology to get full data structure
  transform_setup(topology)
  log.exit_on_error()
  
  # Validate using YANG model
  try:
    errors = validate_topology_yang(topology, args.yang_model)
    
    if errors:
      if args.output == 'json':
        output = json.dumps({'errors': errors}, indent=2)
        print(output)
      else:
        print(f"\nYANG validation found {len(errors)} error(s):\n")
        for error in errors:
          print(f"  - {error}")
        print()
      
      sys.exit(1)
    else:
      if args.output == 'text':
        print("Topology validation passed: all YANG MUST statements satisfied")
      else:
        print(json.dumps({'status': 'valid', 'errors': []}, indent=2))
      sys.exit(0)
      
  except Exception as ex:
    log.fatal(f'YANG validation error: {ex}')

