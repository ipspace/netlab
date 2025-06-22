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

def set_format_tags(data: Box) -> None:
  for v in data.get('results',{}).values():
    if not isinstance(v,Box):
      continue
    for kw in ['timestamp','version','image']:
      if f'_{kw}' in v:
        data._columns[kw] = True

def create_html_page(
      args: argparse.Namespace,
      j2: str,
      data: Box,
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
      args: argparse.Namespace,
      results: Box,
      topology: Box,
      template: str = 'results',
      recursive: bool = True,
      limit: typing.Optional[str] = None) -> None:
  for item,i_data in results.items():
    if item.startswith('_'):
      continue
    if not '_path' in i_data:
      continue
    if limit and item not in limit:
      continue
    path = i_data._path.replace('/','-').replace('#','.')
    create_html_page(args,f'{template}.html.j2',topology + { 'results': i_data },path+".html")
    if recursive:
      create_recursive_html(args,i_data,topology)

def create(
      p_args: argparse.Namespace,
      x_args: typing.List[str],
      results: Box,
      coverage: Box,
      topology: Box) -> None:
  args = parse(x_args)
  if args.release:
    topology._version = __version__

  topology.coverage = coverage
  create_html_page(
    args,
    'index.html.j2',
    topology + { 'results': results },
    'index.html',
    output_dir='.')
  if not args.coverage:
    create_recursive_html(args,results,topology,limit=args.device)
  
  if not args.device:
    create_recursive_html(args,coverage,topology,template='coverage',recursive=False,limit=args.coverage)
