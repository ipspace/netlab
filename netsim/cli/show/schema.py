#
# netlab show schema -- display the JSON schema of lab topologies
#

import argparse
import json

from box import Box

from ...data.schema import topology_schema
from .utils import show_empty_parser


def parse() -> argparse.ArgumentParser:
  parser = show_empty_parser('schema','JSON schema of lab topologies')
  parser.add_argument(
    '--plugin',
    nargs='+',
    dest='plugin',
    action='store',
    help='Add plugin attributes to the system defaults')

  return parser

def show(settings: Box, args: argparse.Namespace) -> None:
  print(json.dumps(topology_schema(settings),indent=2,sort_keys=True))
