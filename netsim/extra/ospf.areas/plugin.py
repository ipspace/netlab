import ipaddress

from box import Box

from netsim import api
from netsim.augment import devices
from netsim.data import merge_with_removed_attributes
from netsim.utils import log
from netsim.utils import routing as _ospf

_config_name = 'ospf.areas'
_requires    = [ 'ospf' ]

'''
Normalize area data -- make sure every area has 'area' attribute that's an IP address
and '_area_int' attribute that's an integer
'''
def normalize_area_data(parent: Box,pname: str) -> bool:
  a_set = set()
  a_OK  = True
  if 'areas' not in parent:                                 # Nothing to do, move on
    return False

  for (a_idx,a_data) in enumerate(parent.areas,start=1):
    if 'area' not in a_data:                                # Make double-sure we have an area or other things will crash
      log.error(
        f'area is missing in {pname}.ospf.areas[{a_idx}]',
        category=log.MissingValue,
        module=_config_name)
      a_OK = False
      continue

    a_data._area_int = int(ipaddress.IPv4Address(a_data.area))
    if a_data._area_int in a_set:                           # Check for duplicate definitions
      log.error(
        f'Duplicate area {a_data.area} definition in {pname}.ospf.areas[{a_idx}]',
        category=log.IncorrectValue,
        module=_config_name)
      a_OK = False
    else:
      a_set.add(a_data._area_int)

    if 'kind' not in a_data:                                # Sanity checks: make sure we have area kind
      a_data.kind = 'regular'
    if a_data.kind in ['nssa','stub']:                      # For NSSA/stub areas
      if 'inter_area' not in a_data:                        # ... assume we want to advertise inter-area LSAs
        a_data.inter_area = True

    for kw in ['external_filter','external_range']:         # External filter/range is applicable only to NSSA areas
      if kw not in a_data:
        continue
      if a_data.kind != 'nssa':
        log.error(
          f'The {kw} parameter can only be specified for NSSA areas ({pname}.ospf.areas[{a_idx}])',
          category=log.IncorrectAttr,
          module=_config_name)
        a_OK = False

  return a_OK

'''
Merge parent area list with target area list. If both lists contain the same area, merge them.
If only the parent list contains an area, copy it into the target area
'''
def merge_ospf_area_list(target: Box, parent: Box) -> None:
  if 'areas' not in parent:
    return
  if 'areas' not in target:
    target.areas = parent.areas
    return

  for a_data in parent.areas:
    a_found = False
    for t_idx,t_data in enumerate(target.areas):
      if t_data._area_int == a_data._area_int:
        a_found = True
        target.areas[t_idx] = merge_with_removed_attributes(t_data,a_data)
        break

    if not a_found:
      target.areas.append(a_data)

'''
Merge global OSPF area definitions with node area definitions and node area definitions with
VRF area definitions.

Note that the global OSPF data is the first item returned by rp_data, so the topology areas
get merged with node areas, and then node areas get merged with VRF areas
'''
def merge_ospf_areas(ndata: Box, topology: Box) -> None:
  for (o_data,_,vrf) in _ospf.rp_data(ndata,'ospf'):
    merge_ospf_area_list(o_data,ndata.get('ospf',{}) if vrf else topology.ospf)

'''
Prune area definitions -- retain only the relevant area definitions in every OSPF block
unless the _prune_areas is set to to False

Returns 'true' if something is left in at least one OSPF instance
'''
def prune_ospf_areas(ndata: Box) -> bool:
  abr_config = False
  for (o_data,o_intf,vrf) in _ospf.rp_data(ndata,'ospf'):
    if 'areas' not in o_data:                               # OSPF areas are not defined, move on
      continue
    if not o_data.get('_prune_areas',True):                 # Do we want full area definition?
      abr_config = True
      continue

    # Get interface areas, normalize them to ints, then select only relevant entries in ospf.areas
    #
    intf_areas = set([ intf.ospf.area for intf in o_intf])
    norm_areas = set([ area if isinstance(area,int) else int(ipaddress.IPv4Address(area)) for area in intf_areas])
    if len(norm_areas) > 1:
      o_data._abr = True

    o_data.areas = [ area for area in o_data.areas if area._area_int in norm_areas ]

    if o_data.areas:                                        # Anything left?
      abr_config = True
    else:
      o_data.pop('areas',None)

  return abr_config

'''
Check whether the node supports all ospf.areas features used in area definitions
'''
def check_node_support(ndata: Box,topology: Box) -> bool:
  OK = devices.FC_MODE.OK
  for (o_data,_,vname) in _ospf.rp_data(ndata,'ospf'):
    if 'areas' not in o_data:
      continue
    path = f'nodes.{ndata.name}' + (f'.vrfs.{vname}' if vname else '')
    for a_entry in o_data.areas:
      stat = devices.check_optional_features(
                data=a_entry,
                path=path+f'.ospf.areas[area={a_entry.area}]',
                node=ndata,
                topology=topology,
                attribute='ospf.areas',
                check_mode=devices.FC_MODE.BLACKLIST)
      if stat.value < OK.value:
        OK = stat
      if stat == devices.FC_MODE.ERR_ATTR:
        return False
  return OK == devices.FC_MODE.OK

'''
post_transform hook

* Normalize ospf.areas parameters in topology and all OSPF instances
* Merge topology/node ospf.areas with node/vrf instances
* Prune the information to include only relevant (used) areas
'''

def post_transform(topology: Box) -> None:
  normalize_area_data(topology.ospf,'topology')

  for ndata in topology.nodes.values():
    if not 'ospf' in ndata.get('module',[]):                # Skip nodes not running OSPF
      continue
    for (o_data,_,vrf) in _ospf.rp_data(ndata,'ospf'):
      normalize_area_data(o_data,f'nodes.{ndata.name}'+(f'vrfs.{vrf}' if vrf else ''))

    merge_ospf_areas(ndata,topology)                        # Now merge topology => node => vrf data
    if prune_ospf_areas(ndata):                             # ... prune that data based on what areas an OSPF instance has
      d_features = devices.get_device_features(ndata,topology.defaults)
      if not d_features.ospf.areas:                         # ... check whether we'll be able to configure the stuff
        log.error(
          f'Device {ndata.device} (node {ndata.name}) does not support OSPF area parameters',
          category=log.IncorrectAttr,
          module=_config_name)
        return

      check_node_support(ndata,topology)                    # Report warnings if a device does not support optional features
      api.node_config(ndata,_config_name)                   # ... and remember that we have to do extra configuration
