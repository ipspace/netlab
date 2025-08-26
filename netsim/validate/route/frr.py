"""
FRR routing table validation routines
"""

import typing

from box import Box

from netsim.data import global_vars
from netsim.utils import routing as _rp_utils


def show_rt_prefix(pfx: str, af: str = 'ipv4', proto: str = '', **kwargs: typing.Any) -> str:
  if af == 'ipv4':
    af = 'ip'

  return f'{af} route' + (' ' + proto if proto else '') + ' json'

def check_rt_metric(p_data: Box, value: typing.Any, result: str) -> typing.Union[str,bool]:
  if p_data.metric == value:
    return f'{result} with metric={value}'
  
  return False

def valid_rt_prefix(
      pfx: str,
      af: str = 'ipv4', 
      state: typing.Optional[str] = None,
      **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  pfx = _rp_utils.get_prefix(pfx)

  if not pfx in _result:
    result_text = f'The prefix {pfx} is not in {af} routing table'
    if state == 'missing':
      return result_text
    else:
      raise Exception(result_text)
  
  p_data = _result[pfx][0]
  result_text = f'Found prefix {pfx} in the {af} routing table'

  for kw in ['metric']:
    if not kw in kwargs:
      continue
    check_func = globals()[f'check_rt_{kw}']
    if not check_func:
      raise Exception(f'Unknown valid_rt_prefix check {kw}')
    for p_instance in p_data:
      result = check_func(p_data,kwargs[kw],result_text)
      if result:
        return result

    raise Exception(f'No prefix {pfx} in the {af} routing table has {kw}={kwargs[kw]}')

  return result_text
