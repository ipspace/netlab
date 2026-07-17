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

        global_acls = topology.routing.get("acl", {})
        node_acls = node.get("routing",{}).get("acl", {})

        for intf in node.interfaces:
           intf_acl = intf.get('routing', {}).get('acl', {})
           for direction in ["in","out"]:
               acl_id =intf_acl.get(direction)
               if not acl_id:
                continue
               if acl_id in global_acls and acl_id not in node_acls:
                        import_routing_object(acl_id, "acl", node, topology)
               elif acl_id not in global_acls:
                  log.error(
                      f"Interface '{intf.ifname}' on '{node.name}' "
                      f"references non-existent ACL '{acl_id}' in 'routing.acl.{direction}'",
                 category=log.IncorrectAttr,
                )



def normalize_acl_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
        normalize_routing_entry(p_entry,p_idx)
        return p_entry



def expand_acl(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
    return None
