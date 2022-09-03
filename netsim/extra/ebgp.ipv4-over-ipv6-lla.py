#
# Simple module to activate ipv4 address family for ipv6 unnumbered eBGP peers
#
# Changes:
# * Sets bgp.activate['ipv4'] = True
#
import typing, netaddr
from box import Box
from netsim import common

"""
activate_ipv4_over_ipv6: Update ebgp neighbors with ipv6 lla to enable ipv4
"""
def activate_ipv4_over_ipv6(node: Box) -> None:

    for n in [n for n in node.bgp.get("neighbors",[]) if 'ipv6' in n and n['ipv6']==True and n.type=='ebgp']:
      if 'activate' in n and 'ipv4' not in n.activate:
        n.activate['ipv4'] = True

def post_transform(topology: Box) -> None:
  for node in topology.nodes.values():
    if "bgp" in node:
        activate_ipv4_over_ipv6(node)
