#
# Custom plugin to collect topology information (vlan ip prefixes, vrf communities) and store them for each node, 
# such that this information can be referenced in custom scripts ( e.g. to create bgp policies )
#
# Configurable via defaults.topology-data, by default this includes all vlans and vrfs
#

from box import Box

"""
Adds a custom node.topology attribute to each node, for use by scripts
"""
def post_transform(topology: Box) -> None:
    sections = topology.defaults.get("topology-data",['vlans','vrfs'])
    to_include = { s: topology[s] for s in sections if s in topology }
    for ndata in topology.nodes.values():
      ndata.topology = to_include
