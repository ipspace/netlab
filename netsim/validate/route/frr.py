"""
FRR OSPFv2 validation routines
"""

from box import Box
import typing
from netsim.data import global_vars
from ..bgp._common import get_pure_prefix

def show_rt_prefix(pfx: str, af: str = 'ipv4', proto: str = '', **kwargs: typing.Any) -> str:
  if af == 'ipv4':
    af = 'ip'

  return f'{af} route' + (' ' + proto if proto else '') + ' json'

def valid_rt_prefix(
      pfx: str,
      af: str = 'ipv4', 
      state: typing.Optional[str] = None,
      **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  pfx = get_pure_prefix(pfx)

  if not pfx in _result:
    result_text = f'The prefix {pfx} is not in {af} routing table'
    if state == 'missing':
      return result_text
    else:
      raise Exception(result_text)
  
  result_text = f'Found prefix {pfx} in the {af} routing table'
  return result_text
