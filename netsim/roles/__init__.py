#
# The "node roles" subsystem appends known (statically defined) node roles modules
# to the topology Plugins (after the user-defined plugins)
#
import typing

from box import Box

from ..data import append_to_list

"""
Return all nodes matching the specified role(s)
"""
def select_nodes_by_role(topology: Box, select: typing.Union[str,list]) -> typing.Generator:
  roles = select if isinstance(select,list) else [ select ]
  for node in topology.nodes.values():
    if node.get('role','router') in roles:
      yield node
  
"""
Initialize the node role subsystem: append all node-handling modules to topology plugins
"""
def init(topology: Box) -> None:
  from . import bridge, host, router

  for role in [ host, router, bridge ]:
    append_to_list(topology,'Plugin',role)
