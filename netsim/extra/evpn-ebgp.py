import typing, netaddr
from box import Box
from netsim import common
from netsim import api
from netsim import data

"""
Adds a custom evpn.as node attribute to build multi-hop eBGP EVPN peerings between loopback interfaces
"""
def init(topology: Box) -> None:
  topology.defaults.evpn.attributes.node.append('as')


"""
For nodes with a custom evpn.as attribute, replace iBGP sessions with eBGP sessions
"""
def post_transform(topology: Box) -> None:
  for name,n in topology.nodes.items():
    if "bgp" in n and "evpn" in n and "as" in n.evpn and n.evpn['as'] != n.bgp['as']:
       n.bgp['as'] = n.evpn['as'] # Update node global BGP AS
       for nb in n.bgp.neighbors:
         if 'evpn' in nb and nb.type == 'ibgp':
            print( f"Replacing iBGP session to {nb.name} with eBGP AS {n.evpn['as']}" )

            nb.local_as = nb['as'] # Use original iBGP AS as local_as override
            # nb.type = 'multihop-ebgp'
            nb.type = 'localas_ibgp'

            # Update neighbor peering data?
            # for p in topology.nodes[nb.name].bgp.neighbors:
            #   if p.name == name and p.type == 'ibgp':
            #     p['as'] = n.bgp['as']
            #     p.type = 'ebgp'
            #     break
