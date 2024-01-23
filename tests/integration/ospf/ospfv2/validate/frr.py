"""
FRR OSPFv2 validation routines
"""

from box import Box
import typing

def show_ospf_neighbor(id: str, present: bool = True) -> str:
  return f'ip ospf neighbor {id} json'

def valid_ospf_neighbor(id: str, present: bool = True) -> bool:
  global _result

  if not id in _result.default:
    if not present:
      return True
    raise Exception(f'There is no OSPF neighbor {id}')
  
  n_state = _result.default[id][0]
  if not present:
    raise Exception(f'Unexpected neighbor {id} in state {n_state.nbrState}')

  if n_state.converged != 'Full':
    raise Exception(f'Neighbor {id} is in state {n_state.nbrState}')

  return True

def show_ospf_prefix(pfx: str, rt: str = '', cost: int = 0) -> str:
  return f'ip ospf route json'

def valid_ospf_prefix(
      pfx: str,
      rt: typing.Optional[str] = None,
      cost: typing.Optional[int] = None) -> str:
  global _result
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  if not pfx in _result:
    raise Exception(f'The prefix {pfx} is not in the OSPF topology')
  
  pfx_data = _result[pfx]
  if rt is not None and rt != pfx_data.routeType:
    raise Exception(f'Invalid OSPF route type for prefix {pfx}: expected {rt} actual {pfx_data.routeType}')

  if cost is not None and cost != pfx_data.cost:
    raise Exception(f'Invalid OSPF end-to-end cost for prefix {pfx}: expected {cost} actual {pfx_data.cost}')

  return True
