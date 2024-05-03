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
  if len(data.keys()) == 1 and 'yml' in data:
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
    if not data[k] or data[k].get('create',None) is False:
      increase_counter(data,'unsupported')
      data[k].supported = False
    OK = True

    if 'caveat' in data[k]:
      if data[k].get('validate',None) is True:
        data[k].pop('caveat',None)

    for step in data[k].keys():
      if step == 'validate' and 'caveat' in data[k]:
        OK = False
        continue

      if data[k][step] is False or step == 'caveat':
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

def is_supported(data: Box, path: str) -> bool:
  for result in data.values():
    if not isinstance(result,Box):
      continue
    if 'up' in result:
      return True
    
  print(f'{path} is unsupported, skipping')
  return False

def add_results(results: Box, top: str, fname: str, path: str) -> None:
  data = Box.from_yaml(filename=f'{top}/{fname}',default_box=True,box_dots=True)
  data = skip_single_key(data)
  data._path = path.replace('.','/').replace('#','.')
  if fname == 'results.yaml' and not is_supported(data,path):
    return
  data = results[path] + data
  if 'results' in fname:
    sum_results(data)
    aggregate_results(results,data,path)
  results[path] = data

def read_results(top: str, results: Box, path: str = '') -> None:
  for fpath in sorted(Path(top).glob('*')):
    fname = fpath.name
    if fname == 'results.yaml' or fname.startswith('_caveats.'):
      add_results(results,top,fname,path)
      continue
    if fname.startswith('.') or fname.startswith('_'):
      continue
    if fpath.is_dir():
      new_path = path + ("." if path else "") + fname.replace('.','#')
      read_results(str(fpath),results,new_path)

SUMMARY_MAP: dict = {
  'supported': 'unsupported',
  'create': 'unsupported',
  'up': 'crashed',
  'config': 'config failed',
  'validate': 'failed'
}

LOG_MAP: dict = {
  'supported': 'create',
  'create': 'create',
  'up': 'up',
  'config': 'initial',
  'validate': 'validate'
}

def summary_results(test_data: Box, log_path: str) -> Box:
  summary = Box(default_box=True,box_dots=True)
  summary.result = '✅'
  for kw in SUMMARY_MAP.keys():
    if kw in test_data and test_data[kw] is False:
      summary.result = SUMMARY_MAP[kw]
      summary.url = f'{log_path}-{LOG_MAP[kw]}.log'
      if summary.result == 'failed' and 'caveat' in test_data:
        summary.result = 'caveat'
      return summary
  
  summary.passed = True
  return summary

def remap_summary(results: Box, remap: Box, path: str) -> None:
  for device in results.keys():
    for platform in results[device].keys():
      data = results[device][platform]
      if not isinstance(data,Box):
        continue

      if path not in data:
        continue

      data = data[path]
      for test,test_data in data.items():
        if test in remap.tests:
          dev_key = f'{device}/{platform}'
          log_path = f"{dev_key}/{path.replace('.','/').replace('#','.')}/{test}.yml"
          summary = summary_results(test_data,log_path)
          remap.results[dev_key][test] = summary
          if 'passed' in summary:
            increase_counter(remap,'pass')
          else:
            increase_counter(remap,summary.result)

def remap_batches(remap: Box) -> None:
  test_keys = list(remap.tests.keys())
  batches = int(len(test_keys)/6) + 1
  batch_size = int(len(test_keys)/batches + 0.999)

  remap._batches = []
  while test_keys:
    if len(test_keys) <= batch_size:
      remap._batches.append(test_keys)
      test_keys = []
    else:
      remap._batches.append(test_keys[:batch_size])
      test_keys = test_keys[batch_size:]

def remap_results(results: Box, remap: typing.Optional[Box] = None, path: str = '') -> Box:
  if remap is None:
    remap = Box.from_yaml(filename=f'map-tests.yml',default_box=True,box_dots=True)

  for k in list(remap.keys()):
    remap_path = f'{path}.{k}' if path else k
    if 'title' in remap[k]:
      remap_summary(results,remap[k],remap_path)
      remap_batches(remap[k])
      remap[k]._path = f'coverage.{remap_path}'
    elif isinstance(remap[k],Box):
      remap[k] = remap_results(results,remap[k],remap_path)
      for kw in remap[k].keys():
        if isinstance(remap[k][kw],Box) and 'title' in remap[k][kw]:
          remap[kw] = remap[k][kw]
      remap.pop(k,None)

  return remap

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
    if '_' in item:
      continue
    if not '_path' in i_data:
      continue
    create_html_page(args,f'{template}.html.j2',topology + { 'results': i_data },i_data._path.replace('/','-')+".html")
    if recursive:
      create_recursive_html(args,i_data,topology)

def create_html_reports(args: argparse.Namespace, results: Box, coverage: Box, topology: Box) -> None:
  create_html_page(
    args,
    'index.html.j2',
    topology + { 'results': results, 'coverage': coverage },
    'index.html',
    output_dir='.')
  create_recursive_html(args,results,topology)
  create_recursive_html(args,coverage,topology,template='coverage',recursive=False)

def main() -> None:
  topology = _read.load('package:cli/empty.yml')
  args = report_parse(sys.argv[1:],topology)
  results = get_empty_box()
  read_results('.',results)
  coverage = remap_results(results)

  if args.yaml:
    print(results.to_yaml())
  elif args.html:
    create_html_reports(args,results,coverage,topology)

if __name__ == '__main__':
  main()
