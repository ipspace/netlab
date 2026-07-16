#
# Generic routing module -- ACL
#

import typing

from box import Box

from .normalize import normalize_routing_entry


def normalize_acl_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
        normalize_routing_entry(p_entry,p_idx)
        return p_entry



def expand_acl(p_name: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
    return None
