"""
Common BGP validation code -- utility functions and such
"""

from box import Box,BoxList
import typing
import netaddr
from ..utils import log

# Find neighbor IP address from neighbor name
def get_bgp_neighbor_id(ngb: list, n_id: str, af: str) -> typing.Union[bool, str]:
  for n in ngb:
    if n.name != n_id:
      continue
    if af not in n:
      continue
    return n[af]
  
  raise Exception(f'Cannot find the {af} address of the neighbor {n_id}')

def get_pure_prefix(pfx: str) -> str:
  pfx_net = netaddr.IPNetwork(pfx)
  pfx = f'{pfx_net.network}/{pfx_net.prefixlen}'
  return pfx

def check_for_prefix(
      pfx: str,
      lookup: typing.Callable,
      data: typing.Union[Box,list],
      table: str = 'routing table',
      state: str = 'present') -> typing.Union[Box,BoxList]:

  result = lookup(pfx,data)
  if result is None:
    stat = f'The prefix {pfx} is not in the {table}'
    if state == 'missing':
      raise log.Result(stat)
    else:
      raise Exception(stat)
  
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
  
  pfx = get_pure_prefix(pfx)
  data = check_for_prefix(pfx,lookup,data,table,state)

  keys = list(checks.keys())
  for k in kwargs:
    if k not in keys:
      raise Exception(f'Invalid prefix check {k}')

  if isinstance(data,Box):
    data = [ data ]

  for k in checks:
    if k in kwargs:
      data = checks[k](data=data,value=kwargs[k],pfx=pfx,state=state,**rest)
      if not data:
        stat = f'There is no path to {pfx} in the {table} with {names[k]}={kwargs[k]}'
        if state != 'missing':
          raise Exception(stat)
        else:
          raise log.Result(stat)
      else:
        if state == 'missing':
          raise Exception(f'The prefix {pfx} with {names[k]}={kwargs[k]} should not be in the {table}')
  
  params = ",".join([ f'{names[k]}={kwargs[k]}' for k in kwargs ])
  if params:
    params = ' with ' + params
  return f'The prefix {pfx} is in the {table}{params}'
