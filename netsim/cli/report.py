#
# netlab report command
#
# Create a text or HTML report from the current lab topology
#
import argparse
import typing

from ..outputs import _TopologyOutput
from ..outputs import common as outputs_common
from ..utils import log
from ..utils import read as _read
from . import _nodeset, load_data_source, parser_add_verbose, parser_data_source


#
# CLI parser for 'netlab report' command
#
def report_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab report",
    description='Create a report from the lab topology data')
  parser.add_argument(
    '--node',
    dest='node', action='store',
    help='Limit the report to selected node(s)')
  parser.add_argument(
    dest='report', action='store',
    help='Name of the report you want to create')
  parser.add_argument(
    dest='output', action='store',
    nargs='?',
    help='Output file name (default: stdout)')
  parser_add_verbose(parser,verbose=False)
  parser_data_source(parser,action='report on')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = report_parse(cli_args)
  topology = load_data_source(args,ghosts=False)
  _read.include_environment_defaults(topology)
  report_module = _TopologyOutput.load(
                     f'report:{args.report}={args.output or "-"}',
                     topology.defaults.outputs.report)
  if not report_module:
    log.fatal('Cannot load the reporting output module, aborting')

  if args.node:
    topology = _nodeset.get_nodeset(topology,_nodeset.parse_nodeset(args.node,topology))

  # Add group variables to topology nodes
  topology = outputs_common.create_adjusted_topology(topology,ignore=[])

  report_module.write(topology)
  if args.output:
    print(f'Created {args.report} report in {args.output}')
