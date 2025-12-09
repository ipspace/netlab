"""
A plugin that removes dhcp.server flag from DHCP clients -- needed to make
dnsmasq fail the DHCP client test at "create the lab" phase
"""

from box import Box


def pre_link_transform(topology: Box) -> None:
  clients = topology.get('groups.dhcp_clients.members',[])
  for c_node in clients:
    c_data = topology.nodes[c_node]
    c_data.pop('dhcp.server',True)
