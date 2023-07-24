#
# netlab inspect command
#
# Inspect data structures in transformed lab topology
#
import typing
import os
import sys
import argparse

from box import Box

from . import load_snapshot
from ..outputs import _TopologyOutput
from ..outputs import common as outputs_common
from ..utils import strings,log

#
# CLI parser for 'netlab inspect' command
#
def inspect_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab inspect",
    description='Inspect data structures in transformed lab topology')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    '--node',
    dest='node', action='store',
    help='Display data for selected node')
  parser.add_argument(
    '--format',
    dest='format', action='store',
    default='yaml',
    choices=['yaml','json'],
    help='Select data presentation format')
  parser.add_argument(
    dest='expr', action='store',
    nargs='?',
    help='Data selection expression')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = inspect_parse(cli_args)
  topology = load_snapshot(args)

  o_module = args.format or 'yaml'
  o_param  = f'{o_module}:{args.expr or "."}'
  inspect_module = _TopologyOutput.load(o_param,topology.defaults.outputs[o_module])

  if args.node:
    if args.node in topology.nodes:
      topology = outputs_common.adjust_inventory_host(
                node=topology.nodes[args.node],
                defaults=topology.defaults,
                group_vars=True)
    else:
      log.fatal(
        f'Unknown node {args.node}\n'+ \
        strings.extra_data_printout(
          f'Valid node names are: {", ".join(list(topology.nodes.keys()))}'),
        module='inspect')

  if inspect_module:
    inspect_module.write(topology)
  else:
    log.fatal('Cannot load the data inspection output module, aborting')
