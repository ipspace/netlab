"""
FRR IS-IS validation routines
"""

import typing

from box import Box

from netsim.data import global_vars
from netsim.utils import routing as _rp_utils


def show_isis_neighbor(id: str, **kwargs: typing.Any) -> str:
  return f'isis neighbor {id} json'

def check_neighbor_state(id: str, state: str, isc: Box) -> None:
 if isc.interface.state != state:
    raise Exception(f'Neighbor {id} in unexpected state {isc.interface.state}')

def check_neighbor_level(id: str, level: str, isc: Box) -> None:
  if 'circuit-type' not in isc.interface:
    raise Exception(f'Unknown IS-IS level for neighbor {id}')
  c_type = isc.interface['circuit-type']
  if c_type != level:
    raise Exception(f"Invalid IS-IS level for neighbor {id}: expected {level} found {c_type}")

def check_neighbor_area(id: str, area: str, isc: Box) -> None:
  if 'area-address' not in isc.interface:
    raise Exception(f'Unknown IS-IS area for neighbor {id}')
  c_area = isc.interface['area-address'].isonet
  if c_area != area:
    raise Exception(f"Invalid IS-IS area for neighbor {id}: expected {area} found {c_area}")

def valid_isis_neighbor(id: str, present: bool = True, state: str = 'Up', level: str = '', area: str='') -> bool:
  _result = global_vars.get_result_dict('_result')

  if 'areas' not in _result:
    if present:
      raise Exception(f'Unknown neighbor {id}')
    else:
      return True

  for isa in _result.areas:
    for isc in isa.get('circuits',{}):
      if 'adj' not in isc:
        continue
      if isc.adj != id:
        continue
      if not present:
        raise Exception(f'Unexpected neighbor {id} in state {isc.interface.state}')
      
      if state:
        check_neighbor_state(id,state,isc)
      if level:
        check_neighbor_level(id,level,isc)
      if area:
        check_neighbor_area(id,area,isc)
      return True

  if not present:
    return True
  else:
    raise Exception(f'No IS-IS neighbor with ID {id}')

def show_isis_prefix(pfx: str, level: str = '2', **kwargs: typing.Any) -> str:
  return f'isis route level-{level} json'

def check_prefix_cost(pfx: str, cost: int, p_info: Box) -> None:
  metric = p_info.get('metric',p_info.get('Metric',None))
  if metric != cost:
    raise Exception(f'Invalid cost for prefix {pfx}: expected {cost} found {metric}')

def valid_isis_prefix(
      pfx: str,
      level: str = '2',
      af: str = 'ipv4',
      present: bool = True,
      cost: typing.Optional[int] = None) -> bool:

  _result = global_vars.get_result_dict('_result')

  pfx = _rp_utils.get_prefix(pfx)

  for isa in _result:
    l_id = f'level-{level}'
    if not l_id in isa:
      continue
    info = isa[l_id]
    if not af in info:
      continue
    pfx_list = info[af]

    for p_info in pfx_list:
      p_pfx = p_info.get('prefix',p_info.get('Prefix',None))
      if p_pfx == pfx:
        if not present:
          raise Exception(f'{af} prefix {pfx} should not be in level-{level} IS-IS database')
        if cost is not None:
          check_prefix_cost(pfx,cost,p_info)
        return True
      
  if not present:
    return True
  raise Exception(f'{af} prefix {pfx} is not in level-{level} IS-IS database')
