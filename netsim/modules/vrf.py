#
# VRF module
#
import typing
from box import Box

from . import _Module,_routing
from . import bfd
from .. import common
from .. import data
from ..data import get_from_box
from ..augment import devices

vrf_id_set: set
vrf_last_id: int

#
# build_vrf_id_set: given an object (topology or node), create a set of RDs
# that appear in that object.
#
def build_vrf_id_set(obj: Box, attr: str) -> set:
  if 'vrfs' in obj:
    return { v[attr] for v in obj.vrfs.values() if isinstance(v,dict) and attr in v and v[attr] is not None }
  return set()

def populate_vrf_id_set(topology: Box) -> None:
  global vrf_id_set, vrf_last_id

  vrf_id_set = build_vrf_id_set(topology,'rd')
  vrf_last_id = 1

  for n in topology.nodes.values():
    if 'vrfs' in n:
      vrf_id_set = vrf_id_set.union(build_vrf_id_set(n,'rd'))

#
# Get a usable AS number. Try bgp.as then vrf.as from node and global settings
#
def get_rd_as_number(obj: Box, topology: Box) -> typing.Optional[typing.Any]:
  return \
    get_from_box(obj,'bgp.as') or \
    get_from_box(obj,'vrf.as') or \
    get_from_box(topology,'bgp.as') or \
    get_from_box(topology,'vrf.as')

#
# Parse rd/rt value -- check whether the RD/RT value is in N:N format
#

def parse_rdrt_value(value: str) -> typing.Optional[typing.List[int]]:
  try:
    (asn,vid) = str(value).split(':')
    return [int(asn),int(vid)]
  except Exception as ex:
    return None

def get_next_vrf_id(asn: str) -> str:
  global vrf_id_set, vrf_last_id

  while f'{asn}:{vrf_last_id}' in vrf_id_set:
    vrf_last_id = vrf_last_id + 1

  rd = f'{asn}:{vrf_last_id}'
  vrf_id_set.add(rd)
  return rd

#
# Normalize VRF IDs -- give a set of VRFs, change integer values of RDs into N:N strings
#

def normalize_vrf_dict(obj: Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return

  asn = None
  obj_name = 'global VRFs' if obj is topology else obj.name

  if not isinstance(obj.vrfs,dict):
    common.error(f'VRF definition in {obj_name} is not a dictionary',common.IncorrectValue,'vrf')
    return

  for vname in list(obj.vrfs.keys()):
    if obj.vrfs[vname] is None:
      obj.vrfs[vname] = {}
    if not isinstance(obj.vrfs[vname],dict):
      common.error(f'VRF definition for {vname} in {obj_name} should be empty or a dictionary',
        common.IncorrectValue,
        'vrf')
      return

    vdata = obj.vrfs[vname]
    if 'rd' in vdata:
      if vdata.rd is None:      # RD set to None can be used to auto-generate RD while preventing RD inheritance
        continue                # ... skip the rest of the checks
      if isinstance(vdata.rd,int):
        asn = asn or get_rd_as_number(obj,topology)
        if not asn:
          common.error(f'VRF {vname} in {obj_name} uses integer RD value without a usable vrf.as or bgp.as AS number',
            common.MissingValue,
            'vrf')
          return
        vdata.rd = f'{asn}:{vdata.rd}'
      elif isinstance(vdata.rd,str):
        if parse_rdrt_value(vdata.rd) is None:
          common.error(f'RD value in VRF {vname} in {obj_name} is not in N:N format',
            common.IncorrectValue,
            'vrf')
      else:
        common.error(f'RD value in VRF {vname} in {obj_name} must be a string or an integer',
          common.IncorrectValue,
          'vrf')

def normalize_vrf_ids(topology: Box) -> None:
  normalize_vrf_dict(topology,topology)

  for n in topology.nodes.values():
    normalize_vrf_dict(n,topology)

#
# Get VRF RD value needed for import/export values. 
#
# WARNING: Global value takes precedence over node value because you might want to change per-node RD
# values for weird topologies like hub-and-spoke
#
def get_vrf_id(vname: str, obj: Box, topology: Box) -> typing.Optional[str]:
  obj_name = 'global VRFs' if obj is topology else obj.name
  vdata = get_from_box(topology,['vrfs',vname]) or get_from_box(obj,['vrfs',vname]) or None

  if vdata is None:
    common.error(
      f'Cannot get VRF ID for unknown VRF {vname} needed in {obj_name}',
      common.MissingValue,
      'vrf')
    return None

  if not isinstance(vdata,Box):
    common.fatal(f'Internal error: got a VRF definition that is not a dictionary')
    return None

  if not 'rd' in vdata:
    common.fatal(f'Internal error: VRF {vname} in {obj_name} should have a RD value by now')
    return None

  return vdata.rd

#
# Set RD values for all VRFs that have no RD attribute or RD value set to None (= auto-generate)
#
def set_vrf_ids(obj: Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return

  asn = None
  obj_name = 'global VRFs' if obj is topology else obj.name

  for vname,vdata in obj.vrfs.items():
    if vdata.get('rd',None) is None:
      asn = asn or get_rd_as_number(obj,topology)
      if not asn:
        common.error('Need a usable vrf.as or bgp.as to create auto-generated VRF RD for {vname} in {obj_name}',
          common.MissingValue,
          'vrf')
        return
      vdata.rd = get_next_vrf_id(asn)

#
# Set import/export route targets
#
def set_import_export_rt(obj : Box, topology: Box) -> None:
  if not 'vrfs' in obj:
    return None

  obj_name = 'global VRFs' if obj is topology else obj.name
  obj_id   = 'vrfs' if obj is topology else f'nodes.{obj.name}.vrfs'
  asn      = None

  for vname,vdata in obj.vrfs.items():
    for rtname in ['import','export']:
      if not rtname in vdata:
        vdata[rtname] = [ vdata.rd ]
        continue

      data.must_be_list(vdata,rtname,f'{obj_id}.{vname}')

      rtlist = []     # The final parsed and looked-up list of RT values
      for rtvalue in vdata[rtname]:
        if isinstance(rtvalue,int):         # RT can be specified as an integer, in which case ASN is prepended to it
          asn = asn or get_rd_as_number(obj,topology)
          if not asn:
            common.error('VRF {vname} in {obj_id} uses integer {rtname} value without a usable vrf.as or bgp.as AS number',
              common.MissingValue,
              'vrf')
            continue
          rtvalue = f'{asn}:{rtvalue}'
        elif not isinstance(rtvalue,str):   # If RT is not an integer, it really should be a string
          common.error('{rtname} value {rtvalue} in VRF {vname} in {obj_id} should be a string or an integer',
            common.IncorrectValue,
            'vrf')
          continue
        else:
          if ':' in rtvalue:                # If there's a colon in RT value, then we're assuming N:N format
            if parse_rdrt_value(rtvalue) is None:
              common.error('{rtname} value {rtvalue} in VRF {vname} in {obj_id} is not in valid N:N format',
                common.IncorrectValue,
                'vrf')
              continue
          else:                             # Otherwise the RT value should refer to another VRF name
            rtvalue = get_vrf_id(rtvalue,obj,topology)
            if rtvalue is None:
              continue            # Error message generated in get_vrf_id

        rtlist.append(rtvalue)

      vdata[rtname] = rtlist

#
# VRF route leaking is usually implemented through BGP VPNv4 address families
# Check whether we have BGP AS configured on all nodes that use VRFs with route leaking
# (identified as import or export RT not equal to [ RD ])
#

def validate_vrf_route_leaking(node : Box) -> None:
  for vname,vdata in node.vrfs.items():
    simple_rt = [ vdata.rd ]
    leaked_routes = vdata['import'] and vdata['import'] != simple_rt
    leaked_routes = leaked_routes or (vdata['export'] and vdata['export'] != simple_rt)
    if leaked_routes and not get_from_box(node,'bgp.as'):
      common.error(
        f"VRF {vname} on {node.name} uses inter-VRF route leaking, but there's no BGP AS configured on the node",
        common.MissingValue,
        'vrf')

class VRF(_Module):

  def module_pre_default(self, topology: Box) -> None:
    for attr_set in ['global','node']:
      if not 'vrfs' in topology.defaults.attributes[attr_set]:
        topology.defaults.attributes[attr_set].append('vrfs')

  def module_pre_transform(self, topology: Box) -> None:
    if not 'vrfs' in topology:
      return

    normalize_vrf_ids(topology)
    populate_vrf_id_set(topology)
    set_vrf_ids(topology,topology)
    set_import_export_rt(topology,topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    if not 'vrfs' in node:
      return

    for vname in node.vrfs.keys():
      if 'vrfs' in topology and vname in topology.vrfs:
        node.vrfs[vname] = topology.vrfs[vname] + node.vrfs[vname]

    set_vrf_ids(node,topology)
    set_import_export_rt(node,topology)

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
          continue
        if not node.vrfs[ifdata.vrf].rd:
          common.error(
            f'VRF {ifdata.vrf} used on an interface in {node.name} does not have a usable RD',
            common.MissingValue,
            'vrf')
          continue

        for af in ['v4','v6']:
          if f'ip{af}' in ifdata:
            node.af[f'vpn{af}'] = True
            node.vrfs[ifdata.vrf].af[f'ip{af}'] = True

    if not vrf_count:                # Remove VRF module from the node if the node has no VRFs
      node.module = [ m for m in node.module if m != 'vrf' ]
    else:
      node.vrfs = node.vrfs or {}     # ... otherwise make sure the 'vrfs' dictionary is not empty
      vrfidx = 100
      for v in node.vrfs.values():    # We need unique VRF index to create OSPF processes
        v.vrfidx = vrfidx
        vrfidx = vrfidx + 1

      validate_vrf_route_leaking(node)
