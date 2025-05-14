'''
Router-specific data transformation

* Add loopback interface data
'''

from box import Box
from ..augment import nodes
from . import select_nodes_by_role

def post_node_transform(topology: Box) -> None:
  for ndata in select_nodes_by_role(topology,'router'):
    nodes.augment_loopback_interface(ndata,topology)
