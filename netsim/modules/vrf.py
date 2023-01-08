#
# VRF module
#
import typing, re
import netaddr
from box import Box

from . import _Module,_routing,_dataplane,get_effective_module_attribute
from .. import common
from .. import data
from ..data import get_from_box,global_vars
from ..data.validate import must_be_list,must_be_dict,validate_attributes
from ..augment import devices,groups
from .. import addressing

#
# Regex expression to validate names used in vrfs. No spaces or weird characters, not too long
# (VRF names are used as device names on Linux, with max 16 characters length)
#
VALID_VRF_NAMES = re.compile( r"[a-zA-Z0-9_.-]{1,16}" )

def populate_vrf_static_ids(topology: Box) -> None:
  for k in ('id','rd'):
    _dataplane.create_id_set(f'vrf_{k}')
    _dataplane.extend_id_set(f'vrf_{k}',_dataplane.build_id_set(topology,'vrfs',k,'topology'))

  _dataplane.set_id_counter('vrf_id',1,4095)

  for n in topology.nodes.values():
    for k in ('id','rd'):
      _dataplane.extend_id_set(f'vrf_{k}',_dataplane.build_id_set(n,'vrfs',k,f'nodes.{n.name}'))

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

def parse_rdrt_value(value: str) -> typing.Optional[typing.List[typing.Union[int,str]]]:
  try:
    (asn,vid) = str(value).split(':')
  except Exception as ex:
    return None

  try:
    return [int(asn),int(vid)]
  except Exception as ex:
    try:
      netaddr.IPNetwork(asn)
      return [asn,int(vid)]
    except Exception as ex:
      return None

def get_next_vrf_id(asn: str) -> typing.Tuple[int,str]:
  rd_set = _dataplane.get_id_set('vrf_rd')
  id_set = _dataplane.get_id_set('vrf_rd')
  while True:
    vrf_id = _dataplane.get_next_id('vrf_id')
    if not f'{asn}:{vrf_id}' in rd_set:
      break

  rd = f'{asn}:{vrf_id}'
  rd_set.add(rd)
  id_set.add(vrf_id)
  return (vrf_id,rd)

#
# Check for 'reasonable' VRF names using a regex expression
#
def validate_vrf_name(name: str) -> None:
  if not VALID_VRF_NAMES.fullmatch( name ):
    common.error(f'VRF name "{name}" does not match the allowed regex expression {VALID_VRF_NAMES.pattern}',
                 common.IncorrectValue,'vrf')

#
# Normalize VRF IDs -- give a set of VRFs, change integer values of RDs into N:N strings
# Also checks for valid naming
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
    validate_vrf_name(vname)
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
          common.error(f'RD value in VRF {vname} in {obj_name} ({vdata.rd}) is not in N:N format',
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

def vrf_needs_id(vrf: Box) -> bool:
  if 'rd' in vrf and 'id' in vrf:
    return False
  return True

def set_vrf_auto_id(vrf: Box, value: typing.Tuple[int,str]) -> None:
  if not 'id' in vrf:
    vrf.id = value[0]

  if not 'rd' in vrf:
    vrf.rd = value[1]

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
    if vrf_needs_id(vdata):
      asn = asn or get_rd_as_number(obj,topology)
      if not asn:
        common.error('Need a usable vrf.as or bgp.as to create auto-generated VRF RD for {vname} in {obj_name}',
          common.MissingValue,
          'vrf')
        return
      set_vrf_auto_id(vdata,get_next_vrf_id(asn))

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

      must_be_list(vdata,rtname,f'{obj_id}.{vname}')

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
    if leaked_routes:
      if not get_from_box(node,'bgp.as'):
        if get_from_box(node,'vrf.as'):
          node.bgp['as'] = node.vrf['as']
        else:
          common.error(
            f"VRF {vname} on {node.name} uses inter-VRF route leaking, but there's no BGP AS configured on the node",
            common.MissingValue,
            'vrf')

def vrf_loopbacks(node : Box, topology: Box) -> None:
  loopback_name = devices.get_device_attribute(node,'loopback_interface_name',topology.defaults) or \
                  devices.get_device_attribute(node,'features.vrf.loopback_interface_name',topology.defaults)

  if not loopback_name:                                                        # pragma: no cover -- hope we got device settings right ;)
    common.print_verbose(f'Device {node.device} used by {node.name} does not support VRF loopback interfaces - skipping assignment.')
    return

  node_vrf_loopback = get_effective_module_attribute(
                        path = 'vrf.loopback',
                        node = node,
                        topology = topology)
  for vrfname,v in node.vrfs.items():
    vrf_loopback = get_from_box(v,'loopback') or node_vrf_loopback          # Do we have VRF loopbacks enabled in the node or in the VRF?
    if not vrf_loopback:                                                    # ... nope, move on
      continue

    ifdata = Box({
      'virtual_interface': True,
      'type': "loopback",
      'name': f'VRF Loopback {vrfname}',
      'ifindex': node.interfaces[-1].ifindex + 1,
      'ifname': loopback_name.format(vrfidx=v.vrfidx,ifindex=v.vrfidx),     # Use VRF-specific and generic loopback index
      'neighbors': [],
      'vrf': vrfname,
    },default_box=True,box_dots=True)

    if isinstance(vrf_loopback,bool):
      vrfaddr = addressing.get(topology.pools, ['vrf_loopback'])
    else:
      vrfaddr = addressing.parse_prefix(vrf_loopback)

    if not vrfaddr:
      continue

    ospf_area = get_effective_module_attribute(
                  path = 'ospf.area',
                  link = v,
                  node = node,
                  topology = topology)

    if ospf_area:
      ifdata.ospf.area = ospf_area

    for af in vrfaddr:
      if af == 'ipv6':
        ifdata[af] = addressing.get_addr_mask(vrfaddr[af],1)
      else:
        ifdata[af] = str(vrfaddr[af])
      vrfaddr[af] = str(ifdata[af])                                         # Save string copy in vrfaddr, we need it later
      node.vrfs[vrfname].af[af] = True                                      # Enable the af if not already

    if not 'networks' in v:                                                 # List of networks to advertise in VRF BGP instance
      v.networks = []

    v.networks.append(vrfaddr)
    node.interfaces.append(ifdata)

    # add loopback addresses to the vrf data as well
    v.loopback_address = vrfaddr

  return

class VRF(_Module):

  def module_pre_default(self, topology: Box) -> None:
    for attr_set in ['global','node']:
      if not 'vrfs' in topology.defaults.attributes[attr_set]:
        topology.defaults.attributes[attr_set].append('vrfs')

  def module_pre_transform(self, topology: Box) -> None:
    if 'groups' in topology:
      groups.export_group_node_data(topology,'vrfs','vrf',copy_keys=['rd','export','import'])

    if not must_be_dict(
        parent=topology,
        key='vrfs',
        path='topology',
        create_empty=False,
        module='vrf'):                                # Check that we're dealing with a VRF dictionary and return if there's none
      return

    for vname in topology.vrfs.keys():
      must_be_dict(
        parent=topology,
        key=f'vrfs.{vname}',
        path='topology',
        create_empty=True,
        module='vrf')

      vdata = topology.vrfs[vname]
      validate_attributes(
        data=vdata,                                     # Validate global VRF data
        topology=topology,
        data_path=f'vrfs.{vname}',                      # Path to global VRF definition
        data_name=f'VRF',
        attr_list=['vrf','link'],                       # We're checking VLAN and link attributes
        modules=topology.get('module',[]),              # ... against global modules
        module_source='topology',
        module='vrf')                                   # Function is called from 'vrf' module

    common.exit_on_error()
    normalize_vrf_ids(topology)
    populate_vrf_static_ids(topology)
    set_vrf_ids(topology,topology)
    set_import_export_rt(topology,topology)

  def node_pre_transform(self, node: Box, topology: Box) -> None:
    # Check if any global vrfs need to be pulled in due to being referenced by a vlan
    vlan_vrfs = [ vdata.vrf for vname,vdata in node.get('vlans',{}).items() if 'vrf' in vdata ]
    if not 'vrfs' in node:
      if not vlan_vrfs:  # No local vrfs and no vlan references -> exit
        return
      node.vrfs = {}     # Prepare to pull in global vrfs

    if not must_be_dict(
        parent=node,
        key='vrfs',
        path=f'nodes.{node.name}',
        create_empty=False,
        module='vrf'):                                # Check that we're dealing with a VRF dictionary and return if there's none
      return

    for vname in set(list(node.vrfs.keys()) + vlan_vrfs):  # Filter out duplicates
      if node.vrfs[vname] is None:
        node.vrfs[vname] = {}

      validate_attributes(
        data=node.vrfs[vname],                        # Validate node VRF data
        topology=topology,
        data_path=f'nodes.{node.name}.vrfs.{vname}',  # Path to node VRF definition
        data_name=f'VRF',
        attr_list=['vrf','link'],                     # We're checking VLAN and link attributes
        modules=node.get('module',[]),                # ... against node modules
        module_source=f'nodes.{node.name}',
        module='vrf')                                 # Function is called from 'vrf' module

      if 'vrfs' in topology and vname in topology.vrfs:
        node.vrfs[vname] = topology.vrfs[vname] + node.vrfs[vname]

    set_vrf_ids(node,topology)
    set_import_export_rt(node,topology)

  def link_pre_transform(self, link: Box, topology: Box) -> None:
    pass

  #
  # The post-link-transform hook must normalize VRF data and pull global VRF data into
  # nodes so we can use the node VRF data in copy_node_data_into_interfaces module function
  #
  # We have to iterate over all VRF interfaces, validate VRF names (which was previously done
  # in post-transform hook), and populate node VRF data (moved from post-transform hook)
  #
  def node_post_link_transform(self, node: Box, topology: Box) -> None:
    for ifdata in node.interfaces:
      if not 'vrf' in ifdata:                                           # Check only VRF interfaces
        continue

      vrf_data_path = f'vrfs.{ifdata.vrf}'
      if not get_from_box(topology,vrf_data_path) and not get_from_box(node,vrf_data_path):
        common.error(
          f'VRF {ifdata.vrf} used on an interface in {node.name} is not defined in the node or globally',
          common.MissingValue,
          'vrf')
        continue

      if not ifdata.vrf in node.vrfs:                                   # Local VRF not present, mark as required
        node.vrfs[ifdata.vrf] = {}

    if not 'vrfs' in node:
      return

    for vname in node.vrfs.keys():
      if vname in topology.get('vrfs',{}):                              # Carefully check for global VRF
        node.vrfs[vname] = topology.vrfs[vname] + node.vrfs[vname]      # ... and do the data merge

  def node_post_transform(self, node: Box, topology: Box) -> None:
    vrf_count = 0

    for ifdata in node.interfaces:
      if 'vrf' in ifdata:
        vrf_count = vrf_count + 1
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

    if common.debug_active('vrf'):
      print( f"vrf node_post_transform on {node.name}: counted {vrf_count} VRFs on interfaces" )
    features = devices.get_device_features(node,topology.defaults)
    if not vrf_count and ('vrf' not in features or not features.vrf.keep_module): # Remove VRF module from the node if the node has no VRFs, unless flag set
      node.module = [ m for m in node.module if m != 'vrf' ]
      node.pop('vrfs',None)
    else:
      node.vrfs = node.vrfs or {}     # ... otherwise make sure the 'vrfs' dictionary is not empty
      vrfidx = 100

      # Check that all VRFs have a well-defined data structure (should be at this point, unless someone used groups.node_data)
      for k,v in node.vrfs.items():
        if v is None or not 'id' in v:
          common.error(
            f"Found invalid VRF {k} on node {node.name}. Did you mention it only in groups.node_data? You can't do that.",
            common.IncorrectValue,
            'vrf')
          common.exit_on_error()

      # We need unique VRF index to create OSPF processes, assign in order sorted by VRF ID "for consistency"
      for v in sorted(node.vrfs.values(),key=lambda v: v.id):
        v.vrfidx = vrfidx
        vrfidx = vrfidx + 1

      validate_vrf_route_leaking(node)

      # Set additional loopbacks (one for each defined VRF)
      vrf_loopbacks(node, topology)

    # Finally, set BGP router ID if we set BGP AS number
    #
    if get_from_box(node,'bgp.as') and not get_from_box(node,'bgp.router_id'):
      _routing.router_id(node,'bgp',topology.pools)
