"""
FRR OSPFv2 validation routines
"""

from box import Box
import typing

# Find neighbor IP address from neighbor name
def get_bgp_neighbor_id(ngb: list, n_id: str, af: str) -> typing.Union[bool, str]:
  for n in ngb:
    if n.name != n_id:
      continue
    if af not in n:
      continue
    return n[af]
  
  raise Exception(f'Cannot find the {af} address of the neighbor {n_id}')

def show_bgp_neighbor(ngb: list, n_id: str, **kwargs: typing.Any) -> str:
  return 'bgp summary json'

def valid_bgp_neighbor(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',
      state: str = 'Established',
      intf: str = '') -> str:
  global _result

  n_addr = get_bgp_neighbor_id(ngb,n_id,af)

  if n_addr is True:
    if not intf:
      raise Exception(f'Need an interface name for an unnumbered EBGP neighbor')
    n_addr = intf
  
  struct_name = f'{af}Unicast'
  if struct_name not in _result:
    raise Exception('There are no BGP peers')

  data = _result[struct_name].peers

  if not n_addr in data:
    raise Exception(f'The router has no BGP neighbor with {af} address {n_addr} ({n_id})')

  if data[n_addr].state not in state:
    raise Exception(f'The neighbor {n_addr} ({n_id}) is in state {data[n_addr].state} (expected {state})')  

  return f'Neighbor {n_addr} ({n_id}) is in state {data[n_addr].state}'

def show_bgp_neighbor_details(ngb: list, n_id: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  n_addr = get_bgp_neighbor_id(ngb,n_id,af)
  return f'bgp neighbor {n_addr} json'

def valid_bgp_neighbor_details(
      ngb: list,
      n_id: str,
      af: str = 'ipv4',**kwargs) -> str:
  global _result

  n_addr = get_bgp_neighbor_id(ngb,n_id,af)
  data = _result[n_addr]

  for k,v in kwargs.items():
    if not k in data:
      raise Exception(f'Neighbor data structure does not contain attribute {k}')
    if data[k] != v:
      raise Exception(f'{k} expected value {v} actual {data[k]}')

  return f'All specified BGP neighbor parameters have the expected values'

def show_bgp_prefix(pfx: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  return f"bgp {af} {pfx} json"

def valid_bgp_prefix(
      pfx: str,
      af: str = 'ipv4',
      state: str = 'present',
      peer: typing.Optional[str] = None,
      nh: typing.Optional[str] = None,
      clusterid: typing.Optional[str] = None) -> str:
  global _result

  exit_miss = f'The prefix {pfx} is not in the BGP table'
  exit_msg = f'The prefix {pfx} is in the BGP table'

  if 'prefix' not in _result:
    if state != 'missing':
      raise Exception(f'The router does not have {pfx} in its BGP table')
    else:
      return exit_miss

  af = 'ip' if af == 'ipv4' else af               # FRR thinks it's IP and IPv6 ;)

  if peer:
    _result.paths = [ p for p in _result.paths if p.peer.routerId == peer ]
    if not _result.paths:
      if state != 'missing':
        raise Exception(f'Peer {peer} does not advertise the BGP prefix {pfx}')
      else:
        return exit_miss

  if _result.paths and state == 'missing':
    raise Exception(f'The prefix {pfx} should not be in the BGP table')

  if nh:                                          # Checking for the next hop
    nh = nh.split('/')[0]                         # Get IP address from a CIDR address
    found_nh = []
    OK = False
    for p_element in _result.paths:
      for nh_element in p_element.nexthops:        
        found_nh.append(nh_element.ip)
        OK = OK or nh_element.ip == nh

    if not OK:
      raise Exception(f'The next hop for prefix {pfx} is {_result.nexthops[0][af]}, not {nh}')

    exit_msg = f'One of the next hops for prefix {pfx} is {nh}'

  if clusterid:
    OK = False
    for p_element in _result.paths:
      if not 'clusterList' in p_element:
        continue
      OK = OK or clusterid in p_element.clusterList.get('list',[])

    if not OK:
      raise Exception(f'Cannot find cluster ID {clusterid} in the paths of prefix {pfx}')

    exit_msg = f'Cluster ID {clusterid} found in at least one path for prefix {pfx}'

  return exit_msg

def show_bgp_prefix_community(pfx: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  return f"bgp {af} {pfx} json"

def valid_bgp_prefix_community(pfx: str, af: str = 'ipv4', state: str = 'present', **kwargs: typing.Any) -> str:
  global _result

  if not valid_bgp_prefix(pfx,af):                          # Offload the baseline processing
    return
  
  OK: dict = {}
  for p_element in _result.paths:                           # Iterate over all know paths for the prefix
    for cname,cvalue in kwargs.items():                     # Iterate over all expected communities
      if cname in p_element:                                # Is the community of this type attached to the path?
        if cvalue in p_element[cname].string:               # Is the expected value there?
          OK[cname] = True

  for cname,cvalue in kwargs.items():                        # Now we know what we found, let's generate some errors
    if state == 'present' and not cname in OK:
      raise Exception(f'{cname} community {cvalue} is not attached to {pfx}')
    if state == 'missing' and cname in OK:
      raise Exception(f'{cname} {cvalue} should not be attached to {pfx}')

  return f"The prefix {pfx} contains the expected communities"

def show_bgp_prefix_aspath(pfx: str, af: str = 'ipv4', **kwargs: typing.Any) -> str:
  return f"bgp {af} {pfx} json"

def valid_bgp_prefix_aspath(pfx: str, aspath: str, af: str = 'ipv4') -> str:
  global _result

  if not valid_bgp_prefix(pfx,af):                          # Offload the baseline processing
    return
  
  for p_element in _result.paths:                           # Iterate over all know paths for the prefix
    if p_element.aspath.string == aspath:
      return f"The prefix {pfx} has the expected AS-path {aspath}"

  raise Exception(f'No path to prefix {pfx} has AS-path {aspath}')
