# Why use Graphite (https://github.com/netreplica/graphite) only with ContainerLab? :-)
#
# With this output module it would be possible to export a topology file to be used within Graphite.
# 
# Graphite container can be launched with:
#
# docker run -d \
#  -v "$(pwd)/graphite-default.json":/var/www/localhost/htdocs/default/default.json \
#  -p 8080:80 \
#  --name graphite \
#  netreplica/graphite:webssh2
#

from array import array
import typing

import json
import os
from box import Box

from .. import common
from . import _TopologyOutput

DEFAULT_NODE_ICON = "router"

def nodes_items(topology: Box) -> list:
    r = []
    for name,n in topology.nodes.items():
        node_icon = DEFAULT_NODE_ICON
        if n.device == 'linux':
            node_icon = 'server'
        node_group = "tier-1"
        node_as = n.get('bgp', {}).get('as')
        if node_as:
            node_group = "as{}".format(node_as)
        r.append(
            {
                'name': name,
                'kind': n.device,
                "ipv4_address": n.mgmt.ipv4,
                "group": node_group,
                "labels": {
                    "graph-level": 1,
                    "graph-icon": node_icon,
                },
            }
        )
    return r

def get_lan_intf_name(topology: Box, node_name: str, bridge_name: str) -> str:
    for intf in topology.nodes[node_name].interfaces:
        if intf.get('bridge','') == bridge_name:
            return intf.ifname
    return "<unknown>"

def links_items(topology: Box) -> list:
    r = []
    for l in topology.links:
        # P2P Links
        if l.type == "p2p":
            r.append(
                {
                    "source": l.left.node,
                    "source_endpoint": l.left.ifname,
                    "target": l.right.node,
                    "target_endpoint": l.right.ifname
                }
            )
        # For now threat LAN Links like a P2P, using only the first two interfaces 
        # TODO: verify additional behaviour
        elif l.type == "lan":
            if l.node_count > 1:
                r.append(
                    {
                        "source": l.interfaces[0].node,
                        "source_endpoint": get_lan_intf_name(topology, l.interfaces[0].node, l.bridge),
                        "target": l.interfaces[1].node,
                        "target_endpoint": get_lan_intf_name(topology, l.interfaces[1].node, l.bridge),
                    }
                )
    return r

class Graphite(_TopologyOutput):

  def write(self, topology: Box) -> None:
    outfile = self.settings.filename or 'graphite-default.json'

    graphite_json = {
        'nodes': nodes_items(topology),
        'links': links_items(topology),
    }

    output = common.open_output_file(outfile)

    output.write(json.dumps(graphite_json, indent=2,sort_keys=True))
    output.write("\n")

    if outfile != '-':
      common.close_output_file(output)
      print("Created Graphite topology file in %s" % outfile)
    else:
      output.write("\n")
