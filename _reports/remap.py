#!/usr/bin/env python3
#
import typing
from box import Box

from .read import increase_counter

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
  for kw in SUMMARY_MAP.keys():
    if kw not in test_data:
      continue

    if isinstance(test_data[kw],Box) and 'warning' in test_data[kw] and summary.status != 'warning':
      summary.result = "<span style='color: orange;'>&#x2714;</span>"
      summary.status = 'warning'
      summary.url = f'{log_path}-{LOG_MAP[kw]}.log'

    if test_data[kw] is False:
      summary.result = SUMMARY_MAP[kw]
      summary.url = f'{log_path}-{LOG_MAP[kw]}.log'
      if summary.result == 'failed' and 'caveat' in test_data:
        summary.result = 'caveat'
      return summary
  
  if 'result' not in summary:
    summary.result = '✅'
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
