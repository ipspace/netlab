'''
Create detailed node-level data structures from topology

* Discover desired imagex (boxes)
* Add default module list to nodes without specific modules
* Set loopback and management interface data
'''

from box import Box

from .. import data
from ..augment import devices
from . import select_nodes_by_role

'''
Create the default static route list from pool prefixes
'''
def default_static_route_list(topology: Box) -> list:
  sr_list = []

  for ap_name,ap_data in topology.addressing.items():
    if ap_name in ['mgmt','router_id']:
      continue

    for af in ['ipv4','ipv6']:
      if not isinstance(ap_data.get(af,False),str):
        continue
      sr_list.append(data.get_box({ af: ap_data[af], '_skip_missing': True, 'nexthop.gateway': True }))

  return sr_list

'''
For all hosts, create 'routing.static' table (unless it exists) that contains
static routes to the first usable default gateway for all pool prefixes or for global
static routes.

* The IPv4 static routes are generated if the node uses IPv4 AF
* The IPv6 static routes are generated if the node uses IPv6 AF and does not listen
  to Router Advertisements

Hosts that have management VRF will get the default static routes, other hosts will
get static routes configured in the 'routing.static.host' parameter or generated from
the address pools.
'''
def add_host_static_routes(topology: Box) -> None:
  sr_list = topology.get('routing.static.host',None)
  sr_default = [ 
    { 'ipv4': '0.0.0.0/0', '_skip_missing': True, 'nexthop.gateway': True },
    { 'ipv6': '::/0', '_skip_missing': True, 'nexthop.gateway': True } ]

  for n_data in select_nodes_by_role(topology,'host'):
    if n_data.get('routing.static',None):         # Host already has static routes, move on
      continue

    # Premature optimization: create the default static route list only when encountering the first host
    if sr_list is None:
      sr_list = default_static_route_list(topology)
    
    features = devices.get_device_features(n_data,topology.defaults)
    host_af_list = [ af for af in n_data.af if af != 'ipv6' or not features.initial.ipv6.use_ra ]
    if 'dhcp' in topology.get('module',[]):       # If we use DHCP module, we have to scan for the DHCP clients
      for af in list(host_af_list):          
        if n_data.get('dhcp.server',False):       # ... unfortunately before the DHCP module post-transform cleanup
          continue                                # ... so we have to skip known DHCP servers
        for intf in n_data.interfaces:            
          if intf.get(f'dhcp.server',None):       # ... as well as DHCP relays
            continue
          if intf.get(f'dhcp.client.{af}',None):  # Now check for the DHCP clients
            host_af_list.remove(af)               # Found a DHCP client interface, remove the AF

    if not host_af_list:                          # Is there anything left to do?
      continue                                    # Nope, no need to muddy the waters

    n_data.routing.static = []
    sr_data = sr_default if features.initial.mgmt_vrf else sr_list
    for af in host_af_list:
      n_data.routing.static += [ data.get_box(sr_entry) for sr_entry in sr_data if af in sr_entry ]

    data.append_to_list(n_data,'module','routing')
    data.append_to_list(topology,'module','routing')

def post_link_transform(topology: Box) -> None:
  add_host_static_routes(topology)
