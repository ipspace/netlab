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


def get_ospf_neighbor_data(data: Box, *, id: str, proto: str, vrf: str = 'default') -> list:
  data = data.get('vrfs',{})

  ngb_list = []
  if vrf in data:
    data = data[vrf]
  else:
    return []

  for v in data.get('instList',{}).values():
    ngb_list += v.get(f'{proto}NeighborEntries',[])

  ngb_list = [ ngb for ngb in ngb_list if ngb.routerId == id ]
  return ngb_list

def show_ospf_neighbor(id: str, present: bool = True, vrf: str = 'default') -> str:
  try:
    ipaddress.IPv4Address(id)
  except:
    raise Exception(f'OSPF router ID {id} is not a valid IP address')
  return f'ip ospf neighbor {id} vrf {vrf} | json'

def valid_ospf_neighbor(
      id: str,
      present: bool = True,
      vrf: str = 'default',*,
      proto: str='ospf',
      proto_name: str = 'OSPFv2') -> bool:
  _result = global_vars.get_result_dict('_result')
  ngb_list = get_ospf_neighbor_data(_result,id=id,proto=proto,vrf=vrf)

  if not ngb_list:
    _common.report_state(
      exit_msg=f'There is no {proto_name} neighbor {id} in VRF {vrf}',
      OK=not present)

  n_state = ngb_list[0]
  if not present:
    raise Exception(f'Unexpected {proto_name} neighbor {id} in state {n_state.adjacencyState}')

  _common.report_state(
    exit_msg=f'{proto_name} neighbor {id} is in state {n_state.adjacencyState}',
    OK=n_state.adjacencyState.startswith('full'))

def show_ospf6_neighbor(id: str, present: bool = True, vrf: str = 'default', **kwargs: typing.Any) -> str:
  try:
    ipaddress.IPv4Address(id)
  except:
    raise Exception(f'OSPFv3 router ID {id} is not a valid IP address')
  return f'ipv6 ospf neighbor {id} vrf {vrf} | json'

def valid_ospf6_neighbor(id: str, present: bool = True,vrf: str = 'default') -> bool:
  return valid_ospf_neighbor(id,present=present,vrf=vrf,proto='ospf3',proto_name='OSPFv3')

def show_ospf_prefix(pfx: str, vrf: str = 'default', **kwargs: typing.Any) -> str:
  return f'ip route vrf {vrf} ospf detail | json'

def get_ospf_prefix(pfx: str, data: Box) -> typing.Optional[Box]:
  for v in data.get('vrfs',{}).values():
    return v.get('routes',{}).get(pfx,None)
  
  return None

def check_ospf_cost(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.metric == value ]

def check_ospf_rt(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  raise log.Skipped('Arista EOS cannot check OSPF route type of installed OSPF routes')

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
  return f'ipv6 route ospf detail | json'

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
            lookup = get_ospf_prefix,
            checks = {
              'cost': check_ospf_cost,
              'rt':   check_ospf_rt },
            names = OSPF_PREFIX_NAMES)
