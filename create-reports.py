#!/usr/bin/env python3
#
import sys
import os
import typing
import argparse
from pathlib import Path
from box import Box
from netsim.data import get_empty_box
from netsim.utils import read as _read,templates

def report_parse(args: typing.List[str], topology: Box) -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description='Created summary reports from automated integration tests')
  parser.add_argument(
    '--html',
    dest='html',
    action='store_true',
    help='Create HTML reports')
  parser.add_argument(
    '--yaml',
    dest='yaml',
    action='store_true',
    help='Print YAML reports')

#  parser_add_verbose(parser)

  return parser.parse_args(args)

def skip_single_key(data: Box) -> Box:
  if len(data.keys()) == 1:
    for k in data.keys():
      return data[k]
    
  for k in data.keys():
    if isinstance(data[k],Box):
      data[k] = skip_single_key(data[k])

  return data

def increase_counter(data: Box, cnt: str) -> None:
  if not cnt in data._count:
    data._count[cnt] = 0

  data._count[cnt] += 1

def sum_results(data: Box) -> None:
  for k in list(data.keys()):
    if k.startswith('_'):
      continue
    if not data[k]:
      increase_counter(data,'unsupported')
    OK = True
    for step in data[k].keys():
      if data[k][step] is False:
        increase_counter(data,step)
        OK = False

    if OK:
      increase_counter(data,'pass')

def aggregate_results(results: Box, data: Box, path: str) -> None:
  while '.' in path:
    path = '.'.join(path.split('.')[:-1])
    if '_path' not in results[path]:
      results[path]._path = path.replace('.','/')
    for k in data._count.keys():
      if k not in results[path]._count:
        results[path]._count[k] = 0

      results[path]._count[k] += data._count[k]

def add_results(results: Box, top: str, path: str) -> None:
  data = Box.from_yaml(filename=f'{top}/results.yaml',default_box=True,box_dots=True)
  data = skip_single_key(data)
  data._path = path.replace('.','/')
  sum_results(data)
  aggregate_results(results,data,path)
  results[path] = data
  return

def read_results(top: str, results: Box, path: str = '') -> None:
  for fpath in Path(top).glob('*'):
    fname = fpath.name
    if fname == 'results.yaml':
      add_results(results,top,path)
      continue
    if '.' in fname or fname.startswith('_'):
      continue
    if fpath.is_dir():
      new_path = path + ("." if path else "") + fname
      read_results(str(fpath),results,new_path)

def create_html_page(args: argparse.Namespace, j2: str, data: Box, fname: str) -> None:
  j2_path = os.path.abspath(os.path.dirname('__file__')) + '/_reports'
  body = templates.render_template(data=data,j2_file=j2,extra_path=['_reports'])
  templates.write_template(
    in_folder=j2_path,j2='page.html.j2',
    data={ 'html': body },
    out_folder='_html',filename=fname)
  print(f'.. created {fname}')

def create_recursive_html(args: argparse.Namespace, results: Box, topology: Box) -> None:
  for item,i_data in results.items():
    if '_' in item:
      continue
    if not '_path' in i_data:
      continue
    create_html_page(args,'results.html.j2',topology + { 'results': i_data },i_data._path.replace('/','-')+".html")
    create_recursive_html(args,i_data,topology)

def create_html_reports(args: argparse.Namespace, results: Box, topology: Box) -> None:
  create_html_page(args,'index.html.j2',topology + { 'results': results },'index.html')
  create_recursive_html(args,results,topology)

def main() -> None:
  topology = _read.load('package:cli/empty.yml')
  args = report_parse(sys.argv[1:],topology)
  results = get_empty_box()
  read_results('.',results)

  if args.yaml:
    print(results.to_yaml())
  elif args.html:
    create_html_reports(args,results,topology)

if __name__ == '__main__':
  main()
