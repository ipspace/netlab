'''
Router-specific data transformation

* Add loopback interface data
'''
import typing

from box import Box, BoxList

from ..utils import log
from ..augment import devices,addressing,links

from . import select_nodes_by_role

'''
Set addresses of the main loopback interface
'''
def loopback_interface(n: Box, pools: Box, topology: Box) -> None:
  n.loopback.type = 'loopback'
  n.loopback.neighbors = []
  n.loopback.virtual_interface = True
  n.loopback.ifindex = 0
  n.loopback.ifname = devices.get_loopback_name(n,topology) or 'Loopback'

  pool = n.get('loopback.pool','loopback')
  prefix_list = addressing.get(pools,[ pool ],n.id)

  for af in prefix_list:
    if prefix_list[af] is True:
      log.error(
        f"Address pool {pool} cannot contain unnumbered/LLA addresses",
        category=log.IncorrectType,
        module='nodes')
    elif not n.loopback[af] and not (prefix_list[af] is False):
      if af == 'ipv6':
        if prefix_list[af].prefixlen == 128:
          n.loopback[af] = str(prefix_list[af])
        else:
          n.loopback[af] = addressing.get_nth_ip_from_prefix(prefix_list[af],1)
      else:
        n.loopback[af] = str(prefix_list[af])
      n.af[af] = True

  for af in log.AF_LIST:
    if af in n.loopback and not isinstance(n.loopback[af],str):
      log.error(
        f'{af} address on the main loopback interface of node {n.name} must be a CIDR prefix',
        category=log.IncorrectType,
        module='nodes')
  
  links.check_interface_host_bits(n.loopback,n)

def post_node_transform(topology: Box) -> None:
  for ndata in select_nodes_by_role(topology,'router'):
    loopback_interface(ndata,topology.pools,topology)
