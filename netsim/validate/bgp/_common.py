"""
Common BGP validation code -- utility functions and such
"""

from box import Box
import typing
import netaddr

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
