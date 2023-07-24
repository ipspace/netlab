#
# netlab report command
#
# Create a text or HTML report from the current lab topology
#
import typing
import argparse

from . import load_snapshot
from ..outputs import _TopologyOutput
from ..utils import strings,log

#
# CLI parser for 'netlab report' command
#
def report_parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    prog="netlab report",
    description='Create a report from the transformed lab topology data')
  parser.add_argument(
    '--snapshot',
    dest='snapshot',
    action='store',
    nargs='?',
    default='netlab.snapshot.yml',
    const='netlab.snapshot.yml',
    help='Transformed topology snapshot file')
  parser.add_argument(
    dest='report', action='store',
    help='Name of the report you want to create')
  parser.add_argument(
    dest='output', action='store',
    nargs='?',
    help='Output file name (default: stdout)')

  return parser.parse_args(args)

def run(cli_args: typing.List[str]) -> None:
  args = report_parse(cli_args)
  topology = load_snapshot(args)
  report_module = _TopologyOutput.load(
                     f'report:{args.report}={args.output or "-"}',
                     topology.defaults.outputs.report)
  if report_module:
    report_module.write(topology)
    if args.output:
      print(f'Created {args.report} report in {args.output}')
  else:
    log.fatal('Cannot load the reporting output module, aborting')
