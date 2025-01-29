#!/usr/bin/env python3
#
import os
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

  return parser.parse_args(args)

def create_html_page(
      args: argparse.Namespace,
      j2: str,
      data: Box,
      output_fname: str,
      output_dir: str = '_html' ) -> None:
  j2_path = os.path.abspath(os.path.dirname('__file__')) + '/_reports'
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
      recursive: bool = True) -> None:
  for item,i_data in results.items():
    if item.startswith('_'):
      continue
    if not '_path' in i_data:
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
  create_recursive_html(args,results,topology)
  create_recursive_html(args,coverage,topology,template='coverage',recursive=False)
