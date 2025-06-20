#!/usr/bin/env python3
#
from pathlib import Path
from box import Box

from netsim import __version__
from netsim.data import get_empty_box
from netsim.utils import read as _read,templates,log

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
    create_status = data[k].get('create',None)
    if not data[k] or create_status is False:
      increase_counter(data,'unsupported')
      data[k].supported = False
    elif isinstance(create_status,Box) and 'warning' in create_status:
      data[k].supported = create_status
    OK = True

    if isinstance(data[k].get('caveat',None),str):                    # Make sure caveat is a list
      data[k].caveat = [ data[k].caveat ]

    if '_warning' in data[k]:                                         # Add warnings to caveats
      if data[k].validate == 'warning':
        data[k].validate = { 'warning': data[k]._warning }            # Migrate "old-style" warnings into boxes
    
    if data[k].get('validate',None) is True:                          # But pop caveats if the validation succeeded
      data[k].pop('caveat',None)

    for step in list(data[k].keys()):
      if isinstance(data[k][step],Box) and 'warning' in data[k][step]:
        increase_counter(data,'warning_'+step)
        if step in ['create','validate']:
          data[k].caveat = data[k].get('caveat',[]) + data[k][step].warning
        OK = True
        continue

      if step in ['config','validate'] and 'caveat' in data[k]:
        OK = False
        continue

      if data[k][step] is False or \
         (step == 'caveat' and (data[k].get('validate') is False or data[k].get('config') is False)):
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

  if log.VERBOSE:  
    print(f'{path} is unsupported, skipping')
  return False

def add_results(results: Box, skip: Box, top: str, fname: str, path: str) -> None:
  data = Box.from_yaml(filename=f'{top}/{fname}',default_box=True,box_dots=True)
  data = skip_single_key(data)
  data._path = path.replace('.','/').replace('#','.')
  r_path = '.'.join(path.split('.')[2:])                              # Get the test path

  if fname == 'results.yaml' and not is_supported(data,path):
    return
  data = results[path] + data
  if r_path in skip:
    for k in skip[r_path]:
      data.pop(k,None)

  if 'results' in fname:
    sum_results(data)
    aggregate_results(results,data,path)
  results[path] = data

def fetch_results(top: str, results: Box, skip: Box, path: str = '') -> None:
  for fpath in sorted(Path(top).glob('*')):
    fname = fpath.name
    if fname == 'results.yaml' or fname.startswith('_caveats.'):
      add_results(results,skip,top=top,fname=fname,path=path)
      continue
    if fname.startswith('.') or fname.startswith('_'):
      continue
    if fpath.is_dir():
      results[path]._children = True
      new_path = path + ("." if path else "") + fname.replace('.','#')
      fetch_results(str(fpath),results,skip=skip,path=new_path)

def read_topology() -> Box:
  return _read.load('package:cli/empty.yml')

def read_setup() -> Box:
  return Box.from_yaml(filename=f'setup.yml',default_box=True,box_dots=True)

def read_results(setup: Box) -> Box:
  results = get_empty_box()
  fetch_results('.',results,skip=setup.skip)
  return results
