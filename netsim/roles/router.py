'''
Router-specific data transformation

* Add loopback interface data
'''
import typing

from box import Box, BoxList

from ..utils import log
from ..augment import devices,addressing,links

from . import select_nodes_by_role

def post_node_transform(topology: Box) -> None:
  pass
