"""
Common BGP validation code -- utility functions and such
"""

import typing

from box import Box, BoxList

from ..utils import log
from ..utils import routing as _rp_utils


# Find neighbor IP address from neighbor name
def get_bgp_neighbor_id(ngb: list, n_id: str, af: str) -> typing.Union[bool, str]:
  for n in ngb:
    if n.name != n_id:
      continue
    if af not in n:
      continue
    return n[af]
  
  raise Exception(f'Cannot find the {af} address of the neighbor {n_id}')

def report_state(exit_msg: str, OK: bool) -> typing.NoReturn:
  if OK:
    raise log.Result(exit_msg)
  else:
    raise Exception(exit_msg)

def check_for_prefix(
      pfx: str,
      lookup: typing.Callable,
      data: typing.Union[Box,list],
      table: str = 'routing table',
      state: str = 'present') -> typing.Union[Box,BoxList]:

  result = lookup(pfx,data)
  if result is None:
    report_state(
      exit_msg=f'The prefix {pfx} is not in the {table}',
      OK=state == 'missing')
  
  if not isinstance(result,Box) and not isinstance(result,BoxList):
    raise Exception('internal error: check_for_prefix got bad result from the lookup function')
  
  return result

def run_prefix_checks(
      pfx: str,
      state: str,
      data: typing.Union[Box,list],
      kwargs: dict,
      table: str,
      lookup: typing.Callable,
      checks: typing.Dict[str,typing.Callable],
      names: dict,
      **rest: typing.Any) -> str:
  
  pfx = _rp_utils.get_prefix(pfx)
  data = check_for_prefix(pfx=pfx,lookup=lookup,data=data,table=table,state=state)

  keys = list(checks.keys())
  for k in kwargs:
    if k not in keys:
      raise Exception(f'Invalid prefix check {k}')

  if isinstance(data,Box):
    data = [ data ]

  checked = []
  params = ''

  for k in checks:
    if k in kwargs:
      data = checks[k](data=data,value=kwargs[k],pfx=pfx,state=state,**rest)

      checked.append(k)
      params = " with " + ",".join([ f'{names[k]}={kwargs[k]}' for k in checked ])
      if not data:
        report_state(
          exit_msg=f'There is no path to {pfx} in the {table}{params}',
          OK=state == 'missing')
      else:
        if state == 'missing':
          raise Exception(f'The prefix {pfx}{params} should not be in the {table}')
  
  if state == 'missing':
    raise Exception(f'The prefix {pfx}{params} should not be in the {table}')

  return f'The prefix {pfx} is in the {table}{params}'
