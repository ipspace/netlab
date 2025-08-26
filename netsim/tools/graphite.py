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


import json

from box import Box

from ..data import get_empty_box
from ..utils import strings
from . import _ToolOutput

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

def nodes_items(topology: Box) -> Box:
    r = get_empty_box()
    for name,n in topology.nodes.items():
        node_icon = (
            n.get('graphite.icon',None) or
            topology.get(f'defaults.devices.{n.device}.graphite.icon',None) or
            DEFAULT_NODE_ICON )
        graph_level = n.get('graphite.level',1)
        node_group = "tier-1"
        node_as = n.get('bgp.as',None)
        if node_as:
            node_group = f"as{node_as}"
        r[name] = {
                'name': name,
                'kind': n.device,
                "mgmt-ipv4-address": n.mgmt.ipv4,
                "mgmt-ipv6-address": "",
                "image": n.box,
                "group": node_group,
                "labels": {
                    "graph-level": graph_level,
                    "graph-icon": node_icon,
                },
            }
    # Special Case:
    # Create a fake node to identify a host bridge, in case there are 1 or more than 2 nodes attached to it.
    for l in topology.links:
        if (l.type == "lan" and l.node_count != 2) or l.type == "stub":
            # Create fake node
            # Inherit graph level and group from first node (l.interfaces[0].node)
            node_item = topology.nodes[l.interfaces[0].node]
            graph_level = node_item.get('graphite.level',1)
            node_group = "tier-1"
            node_as = node_item.get('bgp.as',None)
            if node_as:
                node_group = f"as{node_as}"
            name = strings.eval_format_args(HOST_BRIDGE_NODE_NAME,type=l.type,index=l.linkindex)
            r[name] =  {
                    'name': name,
                    'kind': f"(host bridge: {l.bridge})",
                    "ipv4_address": '',
                    "group": node_group,
                    "labels": {
                        "graph-level": graph_level,
                        "graph-icon": 'expand',
                    },
                }

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
        if l.type == "p2p" or (l.type == "lan" and l.node_count == 2):
            ldata = get_empty_box()
            ldata.a = {
                'node': l.interfaces[0].node,
                'interface': short_ifname(l.interfaces[0].ifname),
                'peer': 'z'
            }
            ldata.z = {
                'node': l.interfaces[1].node,
                'interface': short_ifname(l.interfaces[1].ifname),
                'peer': 'a'
            }
            r.append(ldata)
        elif l.type == "lan" or l.type == "stub":
            for bridge_intf in l.interfaces:
                ldata = get_empty_box()
                bridge_node_name = strings.eval_format_args(
                                     HOST_BRIDGE_NODE_NAME,
                                     type=l.type,
                                     index=l.linkindex)
                ldata.a = {
                    'node': bridge_intf.node,
                    'interface': short_ifname(bridge_intf.ifname),
                    'peer': 'z'
                }
                ldata.z = {
                    'node': bridge_node_name,
                    'interface': '',
                    'peer': 'a'
                }
                r.append(ldata)
    return r

class Graphite(_ToolOutput):

  def write(self, topology: Box, fmt: str) -> str:
    graphite_json = {
        'name': topology.name,
        'type': 'clab',
        'nodes': nodes_items(topology),
        'links': links_items(topology),
    }
    return json.dumps(graphite_json, indent=2,sort_keys=True)
