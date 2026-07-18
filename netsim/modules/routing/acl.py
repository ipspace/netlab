#
# Generic routing module -- ACL
#

import typing

from box import Box

from netsim.utils import log

from .normalize import (
    import_routing_object,
    normalize_routing_entry,
)

"""
Ensure ACLs referenced on interfaces are merged
at node level
"""
def resolve_interface_acl_references(node: Box, topology: Box) -> None:

        routing = topology.get("routing")
        if routing is None:
          return
        global_acls = routing.get("acl", {})

        node_acls = node.get("routing",{}).get("acl", {})

        for intf in node.get("interfaces", []):
           intf_acl = intf.get('routing', {}).get('acl', {})
           for direction in ["in","out"]:
               acl_id =intf_acl.get(direction)
               if not acl_id:
                continue
                if acl_id not in global_acls:
                   log.error(
                       f"Interface '{intf.ifname}' on '{node.name}' "
                       f"references non-existent ACL '{acl_id}' in 'routing.acl.{direction}'",
                       category=log.IncorrectAttr,
                    )
               if acl_id not in node_acls:
                 import_routing_object(acl_id, "acl", node, topology)




def normalize_acl_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
        normalize_routing_entry(p_entry,p_idx)
        return p_entry

"""
expand_acl_address_entry:
* Transform 'pool' and 'prefix' keywords into 'ipv4' and 'ipv6'
* Resolve node inteface and node-role tupples into 'ipv4' and 'ipv6'
"""


def expand_acl_address_entry(p_entry: Box, topology: Box) -> Box:

        extra_data = None
        if 'pool' in p_entry:
                extra_data = topology.addressing[p_entry.pool]
                p_entry.pop('pool',None)

        if 'prefix' in p_entry:
                extra_data = topology.prefix[p_entry.prefix]
                p_entry.pop('prefix',None)

        if 'node' in p_entry:
                node_name = p_entry.node
               
                node_data = topology.nodes[node_name]
                intf_list = node_data.get('interfaces', [])

                if 'interface' in p_entry:
                        ifname = p_entry.interface
                        match = [ intf for intf in intf_list if intf.get('ifname') == ifname ]
                        if not match:
                                log.error(
                                        f'Node {node_name} has no interface {ifname} referenced in ACL entry',
                                        log.IncorrectValue, 'acl')
                                return p_entry
                        extra_data = match[0]
                        p_entry.pop('interface', None)

                elif 'role' in p_entry:
                        role = p_entry.role
                        match = [ intf for intf in intf_list if intf.get('role') == role ]
                        if not match:
                                log.error(
                                        f'Node {node_name} has no interface with role {role} referenced in ACL entry',
                                        log.IncorrectValue, 'acl')
                                return p_entry
                        if len(match) > 1:
                                log.error(
                                        f'Node {node_name} has multiple interfaces with role {role}, ACL entry is ambiguous',
                                        log.IncorrectValue, 'acl')
                                return p_entry
                        extra_data = match[0]
                        p_entry.pop('role', None)

                p_entry.pop('node', None)

        
        if extra_data:                                  
                for af in ('ipv4','ipv6'):                    
                        if af in extra_data:
                                p_entry[af] = extra_data[af]
        return p_entry                                

def expand_acl(p_name: str, o_name: str, node: Box, topology: Box) -> typing.Optional[list]:
  
    acl_list = node.routing[o_name][p_name].value
    for idx, entry in enumerate(list(acl_list)):
        for addr_key in ('src', 'dst'):
            if addr_key in entry:
                entry[addr_key] = expand_acl_address_entry(entry[addr_key], topology)
        acl_list[idx] = entry
    return None
    