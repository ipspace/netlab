#
# Shared normalize/import routines
#
import typing

from box import Box

from ...augment import devices
from ...utils import log

"""
normalize_routing_entry: generic normalization of any list used by the routing module
"""
def normalize_routing_entry(p_entry: typing.Any, p_idx: int) -> typing.Any:
  if not isinstance(p_entry,Box):                 # Skip anything that is not a box, validation will bark
    return p_entry

  if 'action' not in p_entry:                     # Set the default action to 'permit' if missing
    p_entry.action = 'permit'

  if 'sequence' not in p_entry:                   # ... and the default sequence # to 10-times RP entry position
    p_entry.sequence = (p_idx + 1) * 10

  return p_entry

"""
normalize_routing_object: Normalize global- or node routing object data

Please note that this function is called before the data has been validated, so we have to extra-careful
"""
def normalize_routing_object(o_list: list, callback: typing.Callable) -> None:
  for p_idx,p_entry in enumerate(o_list):         # Iterate over routing object entries and normalize them
    o_list[p_idx] = callback(o_list[p_idx],p_idx)

def normalize_routing_objects(
      o_dict: typing.Optional[Box],
      o_type: str,
      normalize_callback: typing.Callable,
      topo_object: bool = False) -> None:

  if o_dict is None:                                        # Nothing to do, I'm OK with that ;)
    return

  if not isinstance(o_dict,Box):                            # Object is not a box, let validation deal with that
    return

  for o_name in list(o_dict.keys()):                        # Iterate over the dictionary
    if o_dict[o_name] is None:                              # if the object value is None, it could be a placeholder
      if topo_object:
        log.error(
          f'Global routing {o_type} {o_name} cannot be None. Use an empty list if you want to have an empty object',
          category=log.IncorrectValue,
          module='routing')
      continue

    if not isinstance(o_dict[o_name],list):                 # Object not a list? Let's make it one ;)
      o_dict[o_name] = [ o_dict[o_name] ]

    normalize_routing_object(o_dict[o_name],normalize_callback)

"""
check_routing_object: validate that a device supports the requested routing object
"""
def check_routing_object(p_name: str,o_type: str, node: Box,topology: Box) -> bool:
  d_features = devices.get_device_features(node,topology.defaults)
  if not d_features.routing[o_type]:
    log.error(
      f"Device {node.device} (node {node.name}) does not support '{o_type}' objects ({p_name})",
      category=log.IncorrectAttr,
      module='routing')
    return False
  
  return True

"""
Import/merge a single global routing object into node routing object table

Return merged routing object or None if the node routing object has not been modified or does not exist
"""
def import_routing_object(pname: str,o_name: str,node: Box,topology: Box) -> typing.Optional[list]:
  topo_pdata = topology.get(f'routing.{o_name}',{})

  # First check whether the node routing object is missing or set to None (no value)
  #
  if pname not in node.routing[o_name] or node.routing[o_name][pname] is None:
    if pname not in topo_pdata:                             # We know we need 'pname', so if it's not in the global policy table
      log.error(                                            # ... we have to throw an error
        f'Global routing {o_name} {pname} referenced in node {node.name} does not exist',
        category=log.MissingValue,
        module='routing')
      return None

    node.routing[o_name][pname] = topo_pdata[pname]         # Otherwise, copy global policy to node policy
    return node.routing[o_name][pname]                      # ... and return it because it might have to be validated

  # OK, we have an existing node routing policy
  if pname not in topo_pdata:                               # Is there anything to merge?
    return None                                             # Nope, exit

  np_data = node.routing[o_name][pname]                     # Prepare for merge: get node- and global entries
  tp_data = topo_pdata[pname]
  sqlist  = [ pe.sequence for pe in np_data ]               # Get the list of sequence numbers from the local policy

  # Now get global entries that are missing in the local policy,
  # add them to the local policy, and sort the result on sequence
  #
  tp_add  = [ pe for pe in tp_data if pe.sequence not in sqlist ]
  if not tp_add:                                            # Nothing to add, get out
    return None

  np_data = sorted(np_data + tp_add, key= lambda x: x.sequence)
  node.routing[o_name][pname] = np_data
  return np_data

"""
Import or merge global routing policies into node routing policies
"""
def process_routing_data(node: Box,o_type: str, topology: Box, dispatch: dict, always_check: bool = True) -> None:

  def call_dispatch(p_name: typing.Union[str,int]) -> None:
    if 'import' in dispatch[o_type]:
      o_import = dispatch[o_type]['import'](p_name,o_type,node,topology)
    else:
      o_import = None
    if o_import is not None or always_check:
      if 'check' in dispatch[o_type]:
        dispatch[o_type]['check'](p_name,o_type,node,topology)
    if 'related' in dispatch[o_type]:
      dispatch[o_type]['related'](p_name,o_type,node,topology)

  if o_type not in dispatch:                         # pragma: no cover
    log.fatal(f'Invalid routing object {o_type} passed to process_routing_data')

  node_pdata = node.get(f'routing.{o_type}',None)
  if node_pdata is None:
    return

  if 'start' in dispatch[o_type]:
    result = dispatch[o_type]['start'](node_pdata,o_type,node,topology)
    if result is not None:
      node.routing[o_type] = result
      node_pdata = result

  if isinstance(node_pdata,dict):
    for p_name in list(node_pdata.keys()):
      call_dispatch(p_name)
  elif isinstance(node_pdata,list):
    for idx in range(len(node_pdata)):
      call_dispatch(idx)

  if 'cleanup' in dispatch[o_type]:
    result = dispatch[o_type]['cleanup'](node_pdata,o_type,node,topology)
