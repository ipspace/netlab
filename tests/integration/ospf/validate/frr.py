"""
FRR OSPFv2 validation routines
"""

from box import Box
import typing

def show_ospf_neighbor(id: str, present: bool = True) -> str:
  return f'ip ospf neighbor {id} json'

def valid_ospf_neighbor(id: str, present: bool = True) -> bool:
  global _result

  if 'default' not in _result:
    raise Exception('OSPF is not running')

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

def show_ospf6_neighbor(id: str, present: bool = True) -> str:
  return f'ipv6 ospf6 neighbor {id} json'

def valid_ospf6_neighbor(id: str, present: bool = True) -> bool:
  global _result

  n_state = None
  for n_idx in _result.keys():
    n_id = n_idx.split('%')[0]                    # Get the router ID (the rest is interface name)
    if n_id == id:                                # Did we find the target neighbor?
      n_state = _result[n_idx]                    # Yes, save the state and get out
      break

  if n_state is None:
    if not present:
      return True
    raise Exception(f'There is no OSPF neighbor {id}')
  else:  
    if not present:
      raise Exception(f'Unexpected neighbor {id} in state {n_state.neighborState}')

  if n_state.neighborState != 'Full':
    raise Exception(f'Neighbor {id} is in state {n_state.neighborState}')

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

def show_ospf6_prefix(pfx: str, rt: str = '', cost: int = 0) -> str:
  return f'ipv6 ospf6 route detail json'

def valid_ospf6_prefix(
      pfx: str,
      rt: typing.Optional[str] = None,
      cost: typing.Optional[int] = None) -> str:
  global _result
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  if 'routes' not in _result:
    raise Exception(f'The OSPFv3 topology has no routes')
  
  _result = _result.routes

  if not pfx in _result:
    raise Exception(f'The prefix {pfx} is not in the OSPF topology')
  
  pfx_data = _result[pfx]
  if rt is not None and rt != pfx_data.pathType:
    raise Exception(f'Invalid OSPF route type for prefix {pfx}: expected {rt} actual {pfx_data.pathType}')

  if cost is not None and cost != pfx_data.metricCost:
    raise Exception(f'Invalid OSPF end-to-end cost for prefix {pfx}: expected {cost} actual {pfx_data.metricCost}')

  return True

def show_ipv6_route(pfx: str, proto: str = '', cost: int = 0) -> str:
  return f'ipv6 route {proto} json'

def valid_ipv6_route(
      pfx: str,
      proto: typing.Optional[str] = None,
      cost: typing.Optional[int] = None) -> str:
  global _result
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  if not _result:
    raise Exception(f'The routing table has no {proto} routes')
  
  if not pfx in _result:
    raise Exception(f'The prefix {pfx} is not in the routing table or not a {proto} route')
  
  pfx_data = _result[pfx][0]
  if cost is not None and cost != pfx_data.metric:
    raise Exception(f'Invalid OSPF end-to-end cost for prefix {pfx}: expected {cost} actual {pfx_data.metric}')

  return True
