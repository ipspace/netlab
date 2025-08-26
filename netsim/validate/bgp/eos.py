"""
Arista EOS BGP validation routines
"""

import typing

from box import Box, BoxList

from netsim.data import global_vars
from netsim.utils import log
from netsim.utils import routing as _rp_utils

from .. import _common
from . import BGP_PREFIX_NAMES, check_community_kw


def check_vrf_data(data: Box, vrf: str, key: str, missing_data: str) -> Box:
  if 'vrfs' not in data:
    raise Exception(f'There are no {missing_data}')

  if vrf not in data.vrfs or key not in data.vrfs[vrf]:
    raise Exception(f'There are no {missing_data} in VRF {vrf}')

  return data.vrfs[vrf][key]

af_lookup: typing.Final[dict] = {
  'ipv4': 'ipv4 unicast',
  'ipv6': 'ipv6 unicast',
  'evpn': 'evpn',
  'vpnv4': 'vpn-ipv4',
  'vpnv6': 'vpn-ipv6'
}

def show_bgp_neighbor(ngb: list, n_id: str, af: str='ipv4', *, activate: str = '', **kwargs: typing.Any) -> str:
  global af_lookup
  if not activate:  
    return 'bgp summary | json'

  if activate not in af_lookup:
    raise Exception(f'Unsupported address family {activate}')

  return f'bgp {af_lookup[activate]} summary | json'

def valid_bgp_neighbor(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',
      state: str = 'Established',
      vrf: str = 'default',
      activate: str = '',
      intf: str = '') -> str:
  _result = global_vars.get_result_dict('_result')

  n_addr = _common.get_bgp_neighbor_id(ngb,n_id,af)

#  if n_addr is True:
#    if not intf:
#      raise Exception(f'Need an interface name for an unnumbered EBGP neighbor')
#    n_addr = intf
  
  data = check_vrf_data(_result,vrf,'peers','BGP peers')

  act_err = f' in address family {activate}' if activate else ''
  if not n_addr in data:
    result = f'The router has no BGP neighbor with {af} address {n_addr} ({n_id}){act_err}'
    if state == 'missing':
      return result
    else:
      raise Exception(result)

  p_state = data[n_addr].peerState
  if p_state not in state:
    result = f'The neighbor {n_addr} ({n_id}){act_err} is in state {data[n_addr].peerState}'
    if state == 'missing' and p_state != 'Established':
      return result
    else:
      raise Exception(f'{result} (expected {state})')  

  return f'Neighbor {n_addr} ({n_id}) is in state {data[n_addr].peerState}'

"""
BGP prefix checks, starting with 'get a BGP prefix from JSON results'
"""
def get_bgp_prefix(pfx: str, data: Box, **kwargs: typing.Any) -> typing.Optional[typing.Union[Box,BoxList]]:
  vrf = kwargs.get('vrf','default')
  data = check_vrf_data(data,vrf,'bgpRouteEntries','BGP route entries')

  return None if pfx not in data else data[pfx].bgpRoutePaths

"""
Select BGP paths with the specified BGP peer (router ID)
"""
def filter_bgp_peer(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.peerEntry.peerAddr == value or p.peerEntry.peerRouterId == value ]

"""
Select BGP paths with the specified next hop

Implements custom exception listing next hops found in the data
"""
def filter_bgp_nh(data: list, value: typing.Any, pfx: str, state: str, **kwargs: typing.Any) -> list:
  value = value.split('/')[0]                         # Get IP address from a CIDR address
  found_nh = []
  result = []
  for p_element in data:
    found_nh.append(p_element.nextHop)
    if p_element.nextHop == value:
      result.append(p_element)

  if not result and state != 'missing':
    raise Exception(f'The next hop(s) for prefix {pfx} is/are {",".join(found_nh)}, not {value}')

  return result

"""
Select the best path(s)
"""
def filter_best(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  result = [ p for p in data if p.get('routeType',{}).get('active',None) == value ]
  return result

"""
Check BGP cluster ID on BGP paths
"""
def check_cluster_id(data: list, value: typing.Any, pfx: str, state: str, **kwargs: typing.Any) -> list:
  result = [ p_element for p_element in data
                if 'routeDetail' in p_element and value in p_element.routeDetail.get('clusterList','') ]

  if not result and state != 'missing':
    raise Exception(f'Cannot find cluster ID {value} in the paths of prefix {pfx}')

  return result

"""
Check BGP local preference
"""
def check_locpref(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.get('localPreference',None) == value ]

"""
Check MED
"""
def check_med(data: list, value: typing.Any, **kwargs: typing.Any) -> list:
  return [ p for p in data if p.get('med',None) == value ]

"""
Check complete AS path
"""
def check_aspath(data: list, value: typing.Any, pfx: str, state: str, **kwargs: typing.Any) -> list:
  result = []
  p_found = []

  for p_element in data:
    if 'asPathEntry' not in p_element:
      continue
    asPath = p_element.asPathEntry.get('asPath',None)
    if asPath == value:
      result.append(p_element)
    elif asPath:
      p_found.append(asPath)

  if not result and state != 'missing':
    raise Exception(f'No path to prefix {pfx} has AS-path {value} (found { ",".join(p_found) })')
  
  return result

"""
Check elements of an AS path
"""
def check_as_elements(data: list, value: typing.Any, pfx: str, state: str, **kwargs: typing.Any) -> list:
  result = []
  p_found = []

  if not isinstance(value,list):
    value = [ value ]

  for p_element in data:
    to_check = [ str(x) for x in value ]
    if 'asPathEntry' not in p_element:
      continue
    asPath = p_element.asPathEntry.get('asPath','')
    asPathList = asPath.split(' ')
    print(f'asp={asPath} asl={asPathList}')
    for asn in asPathList:
      if asn in to_check:
        to_check = [ v for v in to_check if v != asn ]

    if not to_check:
      result.append(p_element)
    else:
      p_found.append(asPath)

  if not result and state != 'missing':
    raise Exception(f'No path to prefix {pfx} has {value} in AS-path (found { ",".join(p_found) })')
  
  return result

"""
Check presence or absence of BGP communities
"""
COMMUNITY_ATTRIBUTE: dict = {
  'community': 'communityList',
  'largeCommunity': 'largeCommunityList'
}

def check_community(data: list, value: typing.Any, pfx: str, state: str, **kwargs: typing.Any) -> list:
  global COMMUNITY_ATTRIBUTE

  if not isinstance(value,dict):
    raise Exception('Community check expects a dictionary of communities')

  OK: dict = {}
  for p_element in data:                                    # Iterate over all know paths for the prefix
    if not 'routeDetail' in p_element:
      continue
    c_data = p_element.routeDetail                          # Get the route detail data if available
    for cname,cvalue in value.items():                      # Iterate over all expected communities
      if cname not in COMMUNITY_ATTRIBUTE:                  # Can we check this community type?
        raise Exception(f'EOS BGP validation plugin cannot check {cname}')
      c_attr = COMMUNITY_ATTRIBUTE[cname]                   # Map standard community name into EOS JSON attribute
      if c_attr in c_data:                                  # Is the community of this type attached to the path?
        if cvalue in c_data[c_attr]:                        # Is the expected value there?
          OK[cname] = True

  for cname,cvalue in value.items():                        # Now we know what we found, let's generate some errors
    check_community_kw(cname)
    if state == 'present' and not cname in OK:
      raise Exception(f'{cname} community {cvalue} is not attached to {pfx}')
    if state == 'missing' and cname in OK:
      raise Exception(f'{cname} {cvalue} should not be attached to {pfx}')

  raise log.Result(f"The prefix {pfx} contains the expected communities")

"""
BGP prefix validation function:

* Use single-prefix show command
* Use the run_prefix_checks framework for validation
"""
def show_bgp_prefix(pfx: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  pfx = _rp_utils.get_prefix(pfx)
  return f"bgp {af} unicast {pfx} | json"

def valid_bgp_prefix(
      pfx: str,*,
      af: str = 'ipv4',
      state: str = 'present',
      vrf: str = 'default',
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
               'med': check_med,
            },
            names = BGP_PREFIX_NAMES,
            vrf = vrf)
