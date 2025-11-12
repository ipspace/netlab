#!/usr/bin/env python3
#
import typing
from box import Box

from .read import increase_counter,get_git_releases
from netsim.data import get_empty_box

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
      supported = False
      dev_key = None
      for test,test_data in data.items():
        if test in remap.tests:
          dev_key = f'{device}/{platform}'
          log_path = f"{dev_key}/{path.replace('.','/').replace('#','.')}/{test}.yml"
          summary = summary_results(test_data,log_path)
          remap.results[dev_key][test] = summary
          if summary.result != 'unsupported':
            supported = True
          if 'passed' in summary:
            increase_counter(remap,'pass')
          else:
            increase_counter(remap,summary.result)

      if not supported and dev_key is not None:
        remap.results.pop(dev_key)

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
    f_path = f'{path}.{k}' if path else k
    remap_path = remap[k].get('from',f_path)
    if 'title' in remap[k]:
      remap_summary(results,remap[k],remap_path)
      remap_batches(remap[k])
      remap[k]._path = f'coverage.{f_path}'
    elif isinstance(remap[k],Box):
      remap[k] = remap_results(results,remap[k],remap_path)
      for kw in remap[k].keys():
        if isinstance(remap[k][kw],Box) and 'title' in remap[k][kw]:
          remap[kw] = remap[k][kw]
      remap.pop(k,None)

  return remap

def remap_release_coverage(topology: Box, tests: Box, results: Box) -> Box:
  devices = topology.defaults.devices + topology.defaults.daemons
  remap_data = get_empty_box()
  releases = get_git_releases()
  release_timestamp = max(releases.values())

  for device in list(results.keys()):
    if device not in devices:
      continue

    dev_data = results[device]
    test_data = None
    for provider in list(dev_data.keys()):
      if provider not in topology.defaults.providers:
        continue

      test_data = dev_data[provider] if test_data is None else test_data + dev_data[provider]

    if test_data is None:
      print(f'No test results for {device}')
      continue

    for t_name,t_setup in tests.items():
      t_path = t_setup.get('from',t_name)
      if t_path not in test_data:
        remap_data[device][t_name] = -1
        continue

      t_scenarios = t_setup.get('tests',{})
      ts_results  = test_data[t_path]
      t_done = len([ test_id for test_id in t_scenarios 
                      if test_id in ts_results 
                        and '_timestamp' in ts_results[test_id]
                        and ts_results[test_id]._timestamp >= release_timestamp])
      remap_data[device][t_name] = int(t_done / len(t_scenarios) * 100)

  return remap_data
