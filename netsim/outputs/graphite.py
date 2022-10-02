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
from .. import data
from . import _TopologyOutput

DEFAULT_NODE_ICON = "router"
HOST_BRIDGE_NODE_NAME = "({type}:{index})"

short_ifname_lookup = {
    'GigabitEthernet': 'ge',
    'Ethernet': 'eth',
    'ethernet': 'eth',
    'ether': 'eth'
}

def short_ifname(n : str) -> str:
    global short_ifname_lookup

    for long_name in short_ifname_lookup.keys():
        if long_name in n:
            return n.replace(long_name,short_ifname_lookup[long_name],1)

    return n

def nodes_items(topology: Box) -> list:
    r = []
    for name,n in topology.nodes.items():
        node_icon = ( data.get_from_box(n,'graphite.icon') or 
            data.get_from_box(topology,f'defaults.devices.{n.device}.graphite.icon') or 
            DEFAULT_NODE_ICON )
        graph_level = data.get_from_box(n,'graphite.level') or 1
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
                    "graph-level": graph_level,
                    "graph-icon": node_icon,
                },
            }
        )
    # Special Case:
    # Create a fake node to identify a host bridge, in case there are 1 or more than 2 nodes attached to it.
    for l in topology.links:
        if (l.type == "lan" and l.node_count != 2) or l.type == "stub":
            # Create fake node
            # Inherit graph level and group from first node (l.interfaces[0].node)
            node_item = topology.nodes[l.interfaces[0].node]
            graph_level = data.get_from_box(node_item,'graphite.level') or 1
            node_group = "tier-1"
            node_as = node_item.get('bgp', {}).get('as')
            if node_as:
                node_group = "as{}".format(node_as)
            r.append(
                {
                    'name': HOST_BRIDGE_NODE_NAME.format(type=l.type, index=l.linkindex),
                    'kind': "(host bridge: {})".format(l.bridge),
                    "ipv4_address": '',
                    "group": node_group,
                    "labels": {
                        "graph-level": graph_level,
                        "graph-icon": 'expand',
                    },
                }
            )
    return r

def get_lan_intf_name(topology: Box, node_name: str, bridge_name: str) -> str:
    for intf in topology.nodes[node_name].interfaces:
        if intf.get('bridge','') == bridge_name:
            return short_ifname(intf.ifname)
    return "<unknown>"

def links_items(topology: Box) -> list:
    r = []
    for l in topology.links:
        # P2P Links
        if l.type == "p2p":
            r.append(
                {
                    "source": l.interfaces[0].node,
                    "source_endpoint": short_ifname(l.interfaces[0].ifname),
                    "target": l.interfaces[1].node,
                    "target_endpoint": short_ifname(l.interfaces[1].ifname)
                }
            )
        elif l.type == "lan" or l.type == "stub":
            # If LAN link have only two interfaces in it, treat it like a P2P
            # - Else, in nodes_items create a fake item that represents the host bridge, and attach the devices to it.
            if l.type == "lan" and l.node_count == 2:
                r.append(
                    {
                        "source": l.interfaces[0].node,
                        "source_endpoint": get_lan_intf_name(topology, l.interfaces[0].node, l.bridge),
                        "target": l.interfaces[1].node,
                        "target_endpoint": get_lan_intf_name(topology, l.interfaces[1].node, l.bridge),
                    }
                )
            else:
                bridge_node_name = HOST_BRIDGE_NODE_NAME.format(type=l.type, index=l.linkindex)
                for bridge_intf in l.interfaces:
                    # Create an attachment
                    r.append(
                        {
                            "source": bridge_node_name,
                            "source_endpoint": "",
                            "target": bridge_intf.node,
                            "target_endpoint": get_lan_intf_name(topology, bridge_intf.node, l.bridge),
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
