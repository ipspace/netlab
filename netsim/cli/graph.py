#
# netlab graph command
#
# Connect a graph description for Graphviz or D2
#
import typing
import argparse

from . import load_snapshot
from ..outputs import _TopologyOutput
from ..utils import strings,log

#
# CLI parser for 'netlab graph' command
#
def graph_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab graph",
    description='Create a graph description in Graphviz or D2 format')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    '-t','--type',
    dest='g_type', action='store',
    choices=['topology,bgp'],
    help='Graph type')
  parser.add_argument(
    '-e','--engine',
    dest='engine', action='store',
    default='graphviz',
    choices=['graphviz','d2'],
    help='Graphing engine')
  parser.add_argument(
    dest='output', action='store',
    nargs='?',
    help='Optional: Output file name')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = graph_parse(cli_args)
  topology = load_snapshot(args)
  o_module = 'graph' if args.engine == 'graphviz' else 'd2'
  o_param  = f'{o_module}:{args.g_type or "topology"}'
  if args.output:
    o_param += f'={args.output}'

  graph_module = _TopologyOutput.load(o_param,topology.defaults.outputs[o_module])
  if graph_module:
    graph_module.write(topology)
  else:
    log.fatal('Cannot load the graphing output module, aborting')
