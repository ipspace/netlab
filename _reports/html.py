#!/usr/bin/env python3
#
import os
import sys
import typing
import argparse
from box import Box

from netsim import __version__
from netsim.utils import templates

def parse(args: typing.List[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Created summary HTML reports from automated integration tests')
  parser.add_argument(
    '--release',
    dest='release',
    action='store_true',
    help='Create release reports')
  parser.add_argument(
    '--device',
    dest='device',
    action='store',
    help='Create the reports only for the specified device')
  parser.add_argument(
    '--coverage',
    dest='coverage',
    action='store',
    help='Create only the specified coverage report')

  return parser.parse_args(args)

def set_format_tags(data: dict) -> None:
  data.pop('_columns',None)
  for v in data.get('results',{}).values():
    if not isinstance(v,dict):
      continue
    for kw in ['timestamp','version','image']:
      if f'_{kw}' in v:
        if '_columns' not in data:
          data['_columns'] = {}
        data['_columns'][kw] = True

def create_html_page(
      j2: str,
      data: dict,
      output_fname: str,
      output_dir: str = '_html' ) -> None:
  j2_path = os.path.abspath(os.path.dirname('__file__')) + '/_reports'
  set_format_tags(data)
  body = templates.render_template(data=data,j2_file=j2,extra_path=['_reports'])
  templates.write_template(
    in_folder=j2_path,j2='page.html.j2',
    data={ 'html': body },
    out_folder=output_dir,filename=output_fname)
  print(f'.. created {output_fname}')

def create_recursive_html(
      results: dict,
      topology: dict,
      template: str = 'results',
      recursive: bool = True,
      limit: typing.Optional[str] = None) -> None:
  for item,i_data in results.items():
    if item.startswith('_'):
      continue
    if not '_path' in i_data:
      continue
    if limit and item not in limit and limit != '*':
      continue
    path = i_data['_path'].replace('/','-').replace('#','.')
    topology['results'] = i_data
    create_html_page(f'{template}.html.j2',topology,path+".html")
    if recursive:
      create_recursive_html(i_data,topology)

def create(
      x_args: typing.List[str],
      results: Box,
      coverage: Box,
      topology: Box) -> None:
  args = parse(x_args)
  if args.release:
    topology._version = __version__

  topology.coverage = coverage
  devices = topology.defaults.devices + topology.defaults.daemons
  for d_name in sorted(list(devices)):
    d_data = devices[d_name]
    if d_name in results:
      results[d_name]._description = d_data.get('description',d_name)
      if 'support.level' in d_data:
        topology.partial_results[d_name] = results[d_name]
      else:
        topology.full_results[d_name] = results[d_name]
    elif not '_meta_device' in d_data:
      topology.no_tests[d_name].description = d_data.description

  topo_dict = topology.to_dict()
  results_dict = results.to_dict()
  coverage_dict = coverage.to_dict()
  topo_dict['results'] = results_dict
  create_html_page(
    'index.html.j2',
    topo_dict,
    'index.html',
    output_dir='.')
  if not args.coverage:
    create_recursive_html(results_dict,topo_dict,template='devices',limit=args.device)
  
  if not args.device:
    create_recursive_html(coverage_dict,topo_dict,template='coverage',recursive=False,limit=args.coverage)

def create_release_coverage(topology: Box, tests: Box, coverage: Box) -> None:
  topo_dict = topology.to_dict()
  topo_dict['coverage'] = coverage.to_dict()
  topo_dict['tests'] = tests.to_dict()
  create_html_page(f'release-coverage.html.j2',topo_dict,"release-coverage.html")
