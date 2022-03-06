#
# VRF module
#
import typing
from box import Box

from . import _Module,_routing
from . import bfd
from .. import common
from ..augment import devices

vrf_id_set: set = set()
vrf_last_id: int = 1

#
# VRF ID handling routing
#
# VRF ID is used to create RD/RT values for VRFs that don't have those values
# explicitely set.
#
def build_vrf_id_set(obj: Box) -> set:
  if 'vrfs' in obj:
    return { v['id'] for v in obj.vrfs.values() if isinstance(v,dict) and 'id' in v }
  return set()

def populate_vrf_id_set(topology: Box) -> None:
  global vrf_id_set

  vrf_id_set = build_vrf_id_set(topology)

  for n in topology.nodes.values():
    if 'vrfs' in n:
      vrf_id_set = vrf_id_set.union(build_vrf_id_set(n))

def get_next_vrf_id() -> int:
  global vrf_id_set, vrf_last_id

  while vrf_last_id in vrf_id_set:
    vrf_last_id = vrf_last_id + 1
  vrf_id_set.add(vrf_last_id)
  return vrf_last_id

#
# Check global or node VRF definitons and set RD/RT values if needed
#
def parse_vrf_attr(vrf: Box, objname: str, vname: str, attr: str) -> typing.Optional[typing.List[int]]:
  if not attr in vrf:
    return None
  try:
    (asn,vid) = str(vrf[attr]).split(':')
    return [int(asn),int(vid)]
  except Exception as ex:
    common.error(f'Invalid {attr} value in {vname} in {objname}\n{ex}',common.IncorrectValue,'vrf')
    return None

def set_vrf_ids(obj: Box, name: str) -> None:
  if not isinstance(obj.vrfs,dict):
    common.error(f'VRF definition in {name} is not a dictionary',common.IncorrectValue,'vrf')
    return

  for vname in list(obj.vrfs.keys()):
    vrf_as = obj.get('vrf',{}).get('as',None)                           # Get VRF ASN
    if not vrf_as:                                                      # If that's not defined, try getting BGP ASN
      vrf_as = obj.get('bgp',{}).get('as',None)

    if obj.vrfs[vname] is None:
      obj.vrfs[vname] = {}
    if not isinstance(obj.vrfs[vname],dict):
      common.error(f'Definition for VRF {vname} in {name} is not a dictionary or empty',common.IncorrectValue,'vrf')
      continue
    for attr in ['rd','import','export']:                               # Iterate over VRF attributes
      if attr in obj.vrfs[vname]:
        if isinstance(obj.vrfs[vname][attr],int):                       # Prepend VRF AS to integer attributes
          if not vrf_as:                                                # But only if vrf.as is defined
            common.error(f'VRF {vname} in {name} is using integer RD/RT value, but vrf.as is not set')
            continue
          obj.vrfs[vname][attr] = f'{vrf_as}:{obj.vrfs[vname][attr]}'
        else:                                                           # VRF attribute should be a string
          parsed_attr = parse_vrf_attr(obj.vrfs[vname],name,vname,attr) # Parse N:N into ASN and ID
          if not parsed_attr:                                           # ... failed to parse, error has already been reported
            continue
          if not 'id' in obj.vrfs[vname]:                               # Use parsed ID as VRF ID if needed
            obj.vrfs[vname].id = parsed_attr[1]
          vrf_as = parsed_attr[0]                                       # Use parsed AS for subsequent attributes if needed

    # We checked existing VRF attributes and extracted ID and/or ASN from them. Now make sure
    # all required VRF attributes are set
    #
    if not 'rd' in obj.vrfs[vname]:                                     # RD is not set
      if not 'id' in obj.vrfs[vname]:                                   # Do we have VRF ID?
        obj.vrfs[vname].id = get_next_vrf_id()                          # ... if not, get the next free ID
      if not vrf_as:                                                    # Hope we have ASN
        common.error(f'VRF {vname} in {name} is using auto-ID, but vrf.as is not set')
        continue
      obj.vrfs[vname].rd = f'{vrf_as}:{obj.vrfs[vname].id}'             # ... cool, we're all set, set RD in ASN:ID format

    for attr in ['import','export']:                                    # If import or export RT is missing
      if not attr in obj.vrfs[vname]:                                   # ... set it to RD
        obj.vrfs[vname][attr] = obj.vrfs[vname].rd

class VRF(_Module):

  def module_pre_default(self, topology: Box) -> None:
    for attr_set in ['global','node']:
      if not 'vrfs' in topology.defaults.attributes[attr_set]:
        topology.defaults.attributes[attr_set].append('vrfs')

  def module_pre_transform(self, topology: Box) -> None:
    if not 'vrfs' in topology:
      return

    populate_vrf_id_set(topology)
    set_vrf_ids(topology,'global VRFs')

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if not 'vrfs' in node:
      return

    set_vrf_ids(node,node.name)

  def link_pre_transform(self, link: Box, topology: Box) -> None:
    pass

  def node_post_transform(self, node: Box, topology: Box) -> None:
    vrf_count = 0
    for ifdata in node.interfaces:
      if 'vrf' in ifdata:
        vrf_count = vrf_count + 1
        if 'vrfs' in topology and ifdata.vrf in topology.vrfs:
          node.vrfs[ifdata.vrf] = topology.vrfs[ifdata.vrf] + node.vrfs[ifdata.vrf]
        if not node.vrfs[ifdata.vrf]:
          common.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} is not defined in the node or globally',
            common.MissingValue,
            'vrf')
        if not node.vrfs[ifdata.vrf].rd:
          common.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} does not have a usable RD',
            common.MissingValue,
            'vrf')

    if not vrf_count:       # Remove VRF module from the node if the node has no VRFs
      node.module = [ m for m in node.module if m != 'vrf' ]
