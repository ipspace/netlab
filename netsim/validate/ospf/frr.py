"""
FRR OSPFv2 validation routines
"""

import ipaddress
import typing

from box import Box

from netsim.data import global_vars
from netsim.utils import log

from .. import _common
from . import OSPF_PREFIX_NAMES


def show_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default') -> str:
  try:
    ipaddress.IPv4Address(id)
  except:
    raise Exception(f'OSPF router ID {id} is not a valid IPv4 address')
  return f'ip ospf ' + (f'vrf {vrf} ' if vrf != 'default' else '') + f'neighbor {id} json'

def valid_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default') -> bool:
  _result = global_vars.get_result_dict('_result')

  if vrf in _result:
    _result = _result[vrf]

  if not id in _result:
    if not present:
      return True
    raise Exception(f'There is no OSPFv2 neighbor {id}')
  
  n_state = _result[id][0]
  if not present:
    raise Exception(f'Unexpected OSPFv2 neighbor {id} in state {n_state.nbrState}')

  exit_msg = f'OSPFv2 neighbor {id} is in state {n_state.nbrState}'
  if not n_state.nbrState.startswith('Full'):
    raise Exception(exit_msg)
  else:
    raise log.Result(exit_msg)

def show_ospf6_neighbor(id: str, **kwargs: typing.Any) -> str:
  try:
    ipaddress.IPv4Address(id)
  except:
    raise Exception(f'OSPF router ID {id} is not a valid IPv4 address')
  return f'ipv6 ospf6 neighbor {id} json'

def valid_ospf6_neighbor(id: str, present: bool = True) -> bool:
  _result = global_vars.get_result_dict('_result')

  n_state = None
  for n_idx in _result.keys():
    n_id = n_idx.split('%')[0]                    # Get the router ID (the rest is interface name)
    if n_id == id:                                # Did we find the target neighbor?
      n_state = _result[n_idx]                    # Yes, save the state and get out
      break

  if n_state is None:
    if not present:
      return True
    raise Exception(f'There is no OSPFv3 neighbor {id}')
  else:  
    if not present:
      raise Exception(f'Unexpected OSPFv3 neighbor {id} in state {n_state.neighborState}')

  if n_state.neighborState != 'Full':
    raise Exception(f'OSPFv3 neighbor {id} is in state {n_state.neighborState}')

  return True

def show_ospf_prefix(pfx: str, **kwargs: typing.Any) -> str:
  return f'ip ospf route json'

def get_ospf_prefix(pfx: str, data: Box) -> typing.Optional[Box]:
  return data.get(pfx,None)

def check_ospf_cost(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  m_value = []
  for p in data:
    c_field = 'type2cost' if 'E2' in p.routeType else 'cost'
    if p[c_field] == value:
      m_value.append(p)

  return m_value

def check_ospf_rt(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.routeType == value ]

def valid_ospf_prefix(
      pfx: str,
      state: str = 'present',
      **kwargs: typing.Any) -> str:

  return _common.run_prefix_checks(
            pfx = pfx,
            state = state,
            data = global_vars.get_result_dict('_result'),
            kwargs = kwargs,
            table = 'OSPF topology',
            lookup = get_ospf_prefix,
            checks = {
              'cost': check_ospf_cost,
              'rt':   check_ospf_rt },
            names = OSPF_PREFIX_NAMES)

def show_ospf6_prefix(pfx: str, **kwargs: typing.Any) -> str:
  return f'ipv6 ospf6 route detail json'

def get_ospf6_prefix(pfx: str, data: Box) -> typing.Optional[Box]:
  return data.get('routes').get(pfx,None)

def check_ospf6_cost(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  m_value = []
  for p in data:
    c_field = 'metricCostE2' if p.pathType == 'External-2' else 'metricCost'
    if p[c_field] == value:
      m_value.append(p)

  return m_value

  return [ p for p in data if p.metricCost == value ]

def check_ospf6_rt(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.pathType == value ]

def valid_ospf6_prefix(
      pfx: str,
      state: str = 'present',
      **kwargs: typing.Any) -> str:

  return _common.run_prefix_checks(
            pfx = pfx,
            state = state,
            data = global_vars.get_result_dict('_result'),
            kwargs = kwargs,
            table = 'OSPFv3 topology',
            lookup = get_ospf6_prefix,
            checks = {
              'cost': check_ospf6_cost,
              'rt':   check_ospf6_rt },
            names = OSPF_PREFIX_NAMES)

def show_ipv6_route(pfx: str, proto: str = '', cost: int = 0) -> str:
  return f'ipv6 route {proto} json'

def valid_ipv6_route(
      pfx: str,
      proto: typing.Optional[str] = None,
      cost: typing.Optional[int] = None) -> typing.Union[str,bool]:
  _result = global_vars.get_result_dict('_result')
  if not isinstance(pfx,str):
    raise Exception(f'Prefix {pfx} is not a string')

  if not _result:
    raise Exception(f'The routing table has no {proto} routes')
  
  if not pfx in _result:
    raise Exception(f'The prefix {pfx} is not in the routing table or not a {proto} route')
  
  pfx_data = _result[pfx][0]
  if cost is not None and cost != pfx_data.metric:
    raise Exception(f'Invalid OSPF end-to-end cost for prefix {pfx}: expected {cost} actual {pfx_data.metric}')

  return f'Prefix {pfx} is in the IPv6 routing table'
