#
# netlab report command
#
# Create a text or HTML report from the current lab topology
#
import typing
import argparse

from . import load_snapshot,_nodeset,parser_lab_location,parser_add_verbose
from ..outputs import _TopologyOutput, common as outputs_common
from ..utils import strings,log

#
# CLI parser for 'netlab report' command
#
def report_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab report",
    description='Create a report from the transformed lab topology data')
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
  parser_lab_location(parser,instance=True,snapshot=True,action='report on')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = report_parse(cli_args)
  topology = load_snapshot(args)
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
