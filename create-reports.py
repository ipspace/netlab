#!/usr/bin/env python3
#
import sys
from box import Box

import _reports.remap
from netsim import __version__
from netsim.utils import log

import _reports

def main() -> None:
  (args,x_args) = _reports.parse.parse(sys.argv[1:])

  log.set_logging_flags(args)
  topology = _reports.read.read_topology()
  setup = _reports.read.read_setup()
  results = _reports.read.read_results(setup)

  coverage = _reports.remap.remap_results(results)
  if args.action == 'yaml':
    _reports.yaml.create(x_args,results)
  elif args.action == 'html':
    _reports.html.create(x_args,results,coverage,topology)
  elif args.action == 'errors':
    _reports.errors.create(x_args,results)
  elif args.action == 'release':
    tests = Box.from_yaml(filename=f'map-tests.yml',default_box=True,box_dots=True)
    coverage = _reports.remap.remap_release_coverage(topology,tests,results)
    _reports.html.create_release_coverage(topology, tests, coverage)
if __name__ == '__main__':
  main()
