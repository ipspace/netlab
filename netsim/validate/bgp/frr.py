"""
FRR BGP validation routines
"""

import typing

from box import Box, BoxList

from netsim.data import global_vars

from ...utils import log
from .. import _common
from . import BGP_PREFIX_NAMES, check_community_kw

af_lookup: typing.Final[dict] = {
  'ipv4': 'ipv4Unicast',
  'ipv6': 'ipv6Unicast',
  'evpn': 'evpn',
  'vpnv4': 'vpnv4',
  'vpnv6': 'vpnv6'
}

af_kw: typing.Final[dict] = {
  'ipv4': 'ipv4 summary established',
  'ipv6': 'ipv6 summary established',
  'evpn': 'evpn summary',
  'vpnv4': 'ipv4 vpn summary',
  'vpnv6': 'ipv6 vpn summary'
}

def show_bgp_neighbor(ngb: list, n_id: str, af: str='ipv4', activate: str = '', **kwargs: typing.Any) -> str:
  global af_lookup

  if not activate:
    return "bgp summary json"

  if activate not in af_lookup:
    raise Exception(f'Unsupport address family {activate}')

  return f"bgp {af_kw[activate]} json"

def valid_bgp_neighbor(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',
      state: str = 'Established',
      activate: str = '',
      intf: str = '') -> str:

  global af_lookup

  _result = global_vars.get_result_dict('_result')
  n_addr = _common.get_bgp_neighbor_id(ngb,n_id,af)

  if n_addr is True:
    if not intf:
      raise Exception(f'Need an interface name for an unnumbered EBGP neighbor')
    n_addr = intf
  
  act_err = f' in address family {activate}' if activate else ''
  if not activate:
    activate = af
  
  struct_name = af_lookup[activate]
  if 'peers' in _result:
    data = _result.peers
  elif struct_name not in _result:
    raise Exception(f'There are no BGP peers in address family {activate}')
  else:
    data = _result[struct_name].peers

  if not n_addr in data:
    result = f'The router has no BGP neighbor with {af} address {n_addr} ({n_id}){act_err}'
    if state == 'missing':
      return result
    else:
      raise Exception(result)

  if data[n_addr].state not in state:
    raise Exception(f'The neighbor {n_addr} ({n_id}) {act_err} is in state {data[n_addr].state} (expected {state})')  

  return f'Neighbor {n_addr} ({n_id}) is in state {data[n_addr].state}'

def show_bgp_neighbor_details(ngb: list, n_id: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  n_addr = _common.get_bgp_neighbor_id(ngb,n_id,af)
  return f'bgp neighbor {n_addr} json'

def valid_bgp_neighbor_details(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',**kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')

  n_addr = _common.get_bgp_neighbor_id(ngb,n_id,af)
  data = _result[n_addr]

  for k,v in kwargs.items():
    if not k in data:
      raise Exception(f'Neighbor data structure does not contain attribute {k}')
    if data[k] != v:
      raise Exception(f'{k} expected value {v} actual {data[k]}')

  return f'All specified BGP neighbor parameters have the expected values'

"""
BGP prefix checks, starting with 'get a BGP prefix from JSON results'
"""
def get_bgp_prefix(pfx: str, data: Box) -> typing.Optional[typing.Union[Box,BoxList]]:
  if 'prefix' not in data:
    return None

  return data.paths

"""
Select BGP paths with the specified BGP peer (router ID)
"""
def filter_bgp_peer(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.peer.routerId == value ]

"""
Select BGP paths with the specified next hop

Implements custom exception listing next hops found in the data
"""
def filter_bgp_nh(data: list, value: typing.Any, pfx: str, state: str) -> list:
  value = value.split('/')[0]                         # Get IP address from a CIDR address
  found_nh = []
  result = []
  for p_element in data:
    for nh_element in p_element.nexthops:
      found_nh.append(nh_element.ip)
      if nh_element.ip == value:
        result.append(p_element)
        break

  if not result and state != 'missing':
    raise Exception(f'The next hop(s) for prefix {pfx} is/are {",".join(found_nh)}, not {value}')

  return result

"""
Select best BGP path(s)
"""
def filter_best(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.get('bestpath',{}).get('overall',None) == value ]


"""
Check BGP cluster ID on BGP paths
"""
def check_cluster_id(data: list, value: typing.Any, pfx: str, state: str) -> list:
  result = [ p_element for p_element in data
                if 'clusterList' in p_element and value in p_element.clusterList.get('list',[]) ]

  if not result and state != 'missing':
    raise Exception(f'Cannot find cluster ID {value} in the paths of prefix {pfx}')

  return result

"""
Check presence or absence of BGP communities
"""
def check_community(data: list, value: typing.Any, pfx: str, state: str) -> list:
  if not isinstance(value,dict):
    raise Exception('Community check expects a dictionary of communities')

  OK: dict = {}
  for p_element in data:                                    # Iterate over all know paths for the prefix
    for cname,cvalue in value.items():                      # Iterate over all expected communities
      if cname in p_element:                                # Is the community of this type attached to the path?
        if cvalue in p_element[cname].string:               # Is the expected value there?
          OK[cname] = True

  for cname,cvalue in value.items():                        # Now we know what we found, let's generate some errors
    check_community_kw(cname)
    if state == 'present' and not cname in OK:
      raise Exception(f'{cname} community {cvalue} is not attached to {pfx}')
    if state == 'missing' and cname in OK:
      raise Exception(f'{cname} {cvalue} should not be attached to {pfx}')

  raise log.Result(f"The prefix {pfx} contains the expected communities")

"""
Check complete AS path
"""
def check_aspath(data: list, value: typing.Any, pfx: str, state: str) -> list:
  result = []
  p_found = []

  for p_element in data:
    if p_element.aspath.string == value:
      result.append(p_element)
    else:
      p_found.append(p_element.aspath.string)

  if not result and state != 'missing':
    raise Exception(f'No path to prefix {pfx} has AS-path {value} (found { ",".join(p_found) })')
  
  return result

"""
Check elements of an AS path
"""
def check_as_elements(data: list, value: typing.Any, pfx: str, state: str) -> list:
  result = []
  p_found = []

  if not isinstance(value,list):
    value = [ value ]

  for p_element in data:
    to_check = list(value)
    for segment in p_element.aspath.segments:
      for asn in segment.get('list',[]):
        if asn in to_check:
          to_check = [ v for v in to_check if v != asn ]

    if not to_check:
      result.append(p_element)
    else:
      p_found.append(p_element.aspath.string)

  if not result and state != 'missing':
    raise Exception(f'No path to prefix {pfx} has {value} in AS-path (found { ",".join(p_found) })')
  
  return result

"""
Check BGP local preference
"""
def check_locpref(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.get('locPrf',None) == value ]

"""
Check MED
"""
def check_med(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.get('metric',None) == value ]

"""
BGP prefix validation function:

* Use single-prefix show command
* Use the run_prefix_checks framework for validation
"""
def show_bgp_prefix(pfx: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  return f"bgp {af} {pfx} json"

def valid_bgp_prefix(
      pfx: str,*,
      af: str = 'ipv4',
      state: str = 'present',
      **kwargs: typing.Any) -> str:
  _result = global_vars.get_result_dict('_result')

  return _common.run_prefix_checks(
            pfx = pfx,
            state = state,
            data = _result,
            kwargs = kwargs,
            table = 'BGP table',
            lookup = get_bgp_prefix,
            checks = {
              'peer': filter_bgp_peer,
              'nh':   filter_bgp_nh,
              'best': filter_best,
              'clusterid': check_cluster_id,
              'community': check_community,
              'as_elements': check_as_elements,
              'aspath': check_aspath,
              'locpref': check_locpref,
              'med': check_med },
            names = BGP_PREFIX_NAMES)
