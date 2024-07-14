#
# Generic routing module: 
#
# * Routing policies (route maps)
# * Routing filters (prefixes, communities, as-paths)
# * Static routes
#
import typing, re
import netaddr
from box import Box

from . import _Module,_routing,_dataplane,get_effective_module_attribute
from ..utils import log
from .. import data
from ..data import global_vars
from ..data.types import must_be_list
from ..augment import devices,groups,links,addressing

def make_list(topology: Box, namespace: str) -> None:
  data = topology.get(namespace,None)
  if data is None:
    return
  
  if not isinstance(data,Box):
    return
  
  for k in list(data.keys()):
    if isinstance(data[k],Box):
      data[k] = [ data[k] ]

class Routing(_Module):
  pass
